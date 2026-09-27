from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import statistics
import time

from evaluator.local_evaluator import (
    catalog_index,
    coarse_category,
    initial_message,
    load_jsonl,
    materialize_hidden_fields,
)
from starter.dense_retrieval import DenseRetriever
from starter.facet_retrieval import FacetRetriever
from starter.intent import parse_intent
from starter.lexical_retrieval import LexicalRetriever
from starter.retrieval import RetrievalHit, build_retrieval_query


ROUTE_NAMES = ("lexical", "facet", "svd_256")
MISS_LIMIT = 5


def stratified_split(samples: list[dict]) -> tuple[list[dict], list[dict]]:
    """Return deterministic 80/20 splits within every scenario."""
    by_scenario: dict[str, list[dict]] = defaultdict(list)
    for sample in samples:
        by_scenario[str(sample["scenario_type"])].append(sample)

    tuning = []
    holdout = []
    for scenario in sorted(by_scenario):
        ordered = sorted(
            by_scenario[scenario],
            key=lambda sample: (
                hashlib.sha256(str(sample["sample_id"]).encode()).hexdigest(),
                str(sample["sample_id"]),
            ),
        )
        cutoff = len(ordered) * 4 // 5
        tuning.extend(ordered[:cutoff])
        holdout.extend(ordered[cutoff:])

    key = lambda sample: str(sample["sample_id"])
    return sorted(tuning, key=key), sorted(holdout, key=key)


def first_turn_query(
    sample: dict,
    categories: dict[str, list[str]],
    products: dict[str, dict],
) -> str:
    """Reconstruct the official first message, then use the M2/TASK-007 path."""
    target = str(sample["ground_truth"]["parent_asin"])
    intent_card, behavior = materialize_hidden_fields(sample, products)
    simulator_sample = {**sample, "intent_card": intent_card, "behavior": behavior}
    message = initial_message(
        simulator_sample,
        coarse_category(categories[target]),
        set(),
    )
    return build_retrieval_query(parse_intent(message).claims)


def execute_routes(
    samples: list[dict],
    retrievers: dict[str, object],
    query_for_sample,
    depth: int,
) -> tuple[
    dict[str, dict[str, list[str]]],
    dict[str, list[float]],
    dict[str, str],
]:
    outcomes: dict[str, dict[str, list[str]]] = {}
    search_times = {name: [] for name in ROUTE_NAMES}
    queries_by_sample_id = {}

    for sample in samples:
        sample_id = str(sample["sample_id"])
        query = query_for_sample(sample)
        queries_by_sample_id[sample_id] = query
        outcomes[sample_id] = {}
        for name in ROUTE_NAMES:
            started = time.perf_counter()
            hits = retrievers[name].search(query, depth)
            search_times[name].append(time.perf_counter() - started)
            outcomes[sample_id][name] = [hit.parent_asin for hit in hits]

    return outcomes, search_times, queries_by_sample_id


def _recall_counts(
    samples: list[dict],
    hit_flags: dict[str, dict[str, bool]],
    field: str,
) -> dict[str, dict[str, dict[str, int]]]:
    counts: dict[str, dict[str, dict[str, int]]] = {}
    for name in (*ROUTE_NAMES, "union"):
        grouped: dict[str, dict[str, int]] = {}
        for sample in samples:
            bucket = str(sample[field])
            grouped.setdefault(bucket, {"hits": 0, "total": 0})
            grouped[bucket]["total"] += 1
            grouped[bucket]["hits"] += int(
                hit_flags[str(sample["sample_id"])][name]
            )
        counts[name] = dict(sorted(grouped.items()))
    return counts


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[math.ceil(len(ordered) * 0.95) - 1]


def summarize_results(
    samples: list[dict],
    outcomes: dict[str, dict[str, list[str]]],
    queries_by_sample_id: dict[str, str],
    build_times: dict[str, float],
    search_times: dict[str, list[float]],
    split: str,
    depth: int,
) -> dict:
    """Use target labels only here to summarize completed retrieval outputs."""
    hit_flags: dict[str, dict[str, bool]] = {}
    unique = {name: 0 for name in ROUTE_NAMES}
    misses = {name: [] for name in (*ROUTE_NAMES, "union")}
    overlap_pairs = (
        ("lexical", "facet"),
        ("lexical", "svd_256"),
        ("facet", "svd_256"),
    )
    overlaps = {f"{left}_{right}": [] for left, right in overlap_pairs}

    for sample in samples:
        sample_id = str(sample["sample_id"])
        target = str(sample["ground_truth"]["parent_asin"])
        candidates = {name: set(outcomes[sample_id][name]) for name in ROUTE_NAMES}
        route_hits = {name: target in candidates[name] for name in ROUTE_NAMES}
        union_candidates = set().union(*candidates.values())
        hit_flags[sample_id] = {**route_hits, "union": target in union_candidates}

        matching_routes = [name for name, hit in route_hits.items() if hit]
        if len(matching_routes) == 1:
            unique[matching_routes[0]] += 1

        for name in (*ROUTE_NAMES, "union"):
            if hit_flags[sample_id][name] or len(misses[name]) >= MISS_LIMIT:
                continue
            retrieved = (
                sorted(union_candidates)
                if name == "union"
                else outcomes[sample_id][name]
            )
            misses[name].append({
                "sample_id": sample_id,
                "query": queries_by_sample_id[sample_id],
                "scenario_type": sample["scenario_type"],
                "difficulty_bucket": sample["difficulty_bucket"],
                "target_parent_asin": target,
                "retrieved_parent_asins": retrieved,
            })

        for left, right in overlap_pairs:
            union = candidates[left] | candidates[right]
            overlap = len(candidates[left] & candidates[right]) / len(union) if union else 0.0
            overlaps[f"{left}_{right}"].append(overlap)

    sample_count = len(samples)
    route_recall = {
        name: round(
            sum(hit_flags[str(sample["sample_id"])][name] for sample in samples)
            / sample_count,
            6,
        )
        for name in ROUTE_NAMES
    }
    pairwise_overlap = {
        name: round(statistics.fmean(values), 6) if values else 0.0
        for name, values in overlaps.items()
    }

    return {
        "split": split,
        "depth": depth,
        "sample_count": sample_count,
        "queries_by_sample_id": queries_by_sample_id,
        "route_recall_at_k": route_recall,
        "union_recall_at_k": round(
            sum(hit_flags[str(sample["sample_id"])]["union"] for sample in samples)
            / sample_count,
            6,
        ),
        "unique_target_contribution": unique,
        "mean_pairwise_jaccard_overlap": {
            **pairwise_overlap,
            "overall": round(statistics.fmean(pairwise_overlap.values()), 6),
        },
        "build_time_seconds": {
            name: round(build_times[name], 6) for name in ROUTE_NAMES
        },
        "mean_search_time_seconds": {
            name: round(statistics.fmean(search_times[name]), 6)
            for name in ROUTE_NAMES
        },
        "p95_search_time_seconds": {
            name: round(_p95(search_times[name]), 6) for name in ROUTE_NAMES
        },
        "scenario_recall_counts": _recall_counts(
            samples, hit_flags, "scenario_type"
        ),
        "difficulty_recall_counts": _recall_counts(
            samples, hit_flags, "difficulty_bucket"
        ),
        "representative_misses": misses,
    }


def compare_routes(
    samples: list[dict],
    products: dict[str, dict],
    categories: dict[str, list[str]],
    split: str,
    depth: int,
) -> dict:
    factories = {
        "lexical": LexicalRetriever,
        "facet": FacetRetriever,
        "svd_256": lambda records: DenseRetriever(records, dimensions=256),
    }
    retrievers = {}
    build_times = {}
    for name in ROUTE_NAMES:
        started = time.perf_counter()
        retrievers[name] = factories[name](products)
        build_times[name] = time.perf_counter() - started

    outcomes, search_times, queries_by_sample_id = execute_routes(
        samples,
        retrievers,
        lambda sample: first_turn_query(sample, categories, products),
        depth,
    )
    return summarize_results(
        samples,
        outcomes,
        queries_by_sample_id,
        build_times,
        search_times,
        split,
        depth,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare M3 retrieval routes")
    parser.add_argument("--split", choices=("tuning", "holdout"), required=True)
    parser.add_argument("--depth", type=int, required=True)
    parser.add_argument("--catalog", default="data/catalog.jsonl")
    parser.add_argument("--dataset", default="data/public_set.jsonl")
    parser.add_argument("--output")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    samples = load_jsonl(args.dataset)
    tuning, holdout = stratified_split(samples)
    selected = tuning if args.split == "tuning" else holdout
    _, categories, products = catalog_index(args.catalog)
    result = compare_routes(selected, products, categories, args.split, args.depth)
    output = json.dumps(result, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    print(output, end="")


if __name__ == "__main__":
    main()
