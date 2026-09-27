from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import statistics
import time

from evaluator.local_evaluator import catalog_index, load_jsonl
from experiments.m3_compare_routes import first_turn_query, stratified_split
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize
from starter.dense_retrieval import _document
from starter.retrieval import RetrievalHit


VARIANT_NAMES = ("raw_tfidf", "svd_64", "svd_256")
MISS_LIMIT = 5


class DenseVariantIndex:
    """Build three dense-vectorization variants over one shared TF-IDF matrix."""

    def __init__(self, records: dict[str, dict[str, object]]) -> None:
        self.parent_asins = tuple(records)
        documents = [_document(record) for record in records.values()]

        started = time.perf_counter()
        self.vectorizer = TfidfVectorizer(max_features=20_000)
        self.raw_vectors = normalize(self.vectorizer.fit_transform(documents))
        tfidf_time = time.perf_counter() - started

        self.svd_models = {}
        self.svd_vectors = {}
        self.build_times = {"raw_tfidf": tfidf_time}
        for name, requested_dimensions in (("svd_64", 64), ("svd_256", 256)):
            started = time.perf_counter()
            dimensions = min(
                requested_dimensions,
                self.raw_vectors.shape[0],
                self.raw_vectors.shape[1],
            )
            model = TruncatedSVD(n_components=dimensions, random_state=0)
            self.svd_models[name] = model
            self.svd_vectors[name] = normalize(model.fit_transform(self.raw_vectors))
            self.build_times[name] = tfidf_time + time.perf_counter() - started

    def search(self, query: str, depth: int) -> dict[str, tuple[RetrievalHit, ...]]:
        hits, _ = self.search_with_timings(query, depth)
        return hits

    def search_with_timings(
        self, query: str, depth: int
    ) -> tuple[dict[str, tuple[RetrievalHit, ...]], dict[str, float]]:
        if depth <= 0 or not query.strip():
            return (
                {name: () for name in VARIANT_NAMES},
                {name: 0.0 for name in VARIANT_NAMES},
            )

        query_tfidf = normalize(self.vectorizer.transform([query]))
        if query_tfidf.nnz == 0:
            return (
                {name: () for name in VARIANT_NAMES},
                {name: 0.0 for name in VARIANT_NAMES},
            )

        hits = {}
        timings = {}

        started = time.perf_counter()
        scores = (self.raw_vectors @ query_tfidf.T).toarray().ravel()
        hits["raw_tfidf"] = self._rank(scores, depth)
        timings["raw_tfidf"] = time.perf_counter() - started

        for name in ("svd_64", "svd_256"):
            started = time.perf_counter()
            query_vector = normalize(self.svd_models[name].transform(query_tfidf))[0]
            scores = self.svd_vectors[name] @ query_vector
            hits[name] = self._rank(scores, depth)
            timings[name] = time.perf_counter() - started

        return hits, timings

    def _rank(self, scores, depth: int) -> tuple[RetrievalHit, ...]:
        ordered = sorted(
            zip(self.parent_asins, scores, strict=True),
            key=lambda item: (-item[1], item[0]),
        )
        return tuple(
            RetrievalHit(parent_asin, rank, float(score))
            for rank, (parent_asin, score) in enumerate(ordered[:depth], start=1)
        )


def execute_variants(
    samples: list[dict],
    index: DenseVariantIndex,
    query_for_sample,
    depth: int,
) -> tuple[
    dict[str, dict[str, list[str]]],
    dict[str, list[float]],
    dict[str, str],
]:
    outcomes = {}
    search_times = {name: [] for name in VARIANT_NAMES}
    queries_by_sample_id = {}

    for sample in samples:
        sample_id = str(sample["sample_id"])
        query = query_for_sample(sample)
        queries_by_sample_id[sample_id] = query

        hits_by_variant, timings = index.search_with_timings(query, depth)
        outcomes[sample_id] = {
            name: [hit.parent_asin for hit in hits_by_variant[name]]
            for name in VARIANT_NAMES
        }
        for name in VARIANT_NAMES:
            search_times[name].append(timings[name])

    return outcomes, search_times, queries_by_sample_id


def _recall_counts(
    samples: list[dict],
    hit_flags: dict[str, dict[str, bool]],
    field: str,
) -> dict[str, dict[str, dict[str, int]]]:
    counts = {}
    for name in (*VARIANT_NAMES, "union"):
        grouped: dict[str, dict[str, int]] = defaultdict(
            lambda: {"hits": 0, "total": 0}
        )
        for sample in samples:
            bucket = str(sample[field])
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
    depth: int,
) -> dict:
    """Use target labels only here to evaluate completed retrieval outputs."""
    hit_flags = {}
    unique = {name: 0 for name in VARIANT_NAMES}
    misses = {name: [] for name in (*VARIANT_NAMES, "union")}
    overlap_pairs = (
        ("raw_tfidf", "svd_64"),
        ("raw_tfidf", "svd_256"),
        ("svd_64", "svd_256"),
    )
    overlaps = {f"{left}_{right}": [] for left, right in overlap_pairs}

    for sample in samples:
        sample_id = str(sample["sample_id"])
        target = str(sample["ground_truth"]["parent_asin"])
        ranked = {
            name: outcomes[sample_id][name][:depth] for name in VARIANT_NAMES
        }
        candidates = {name: set(ids) for name, ids in ranked.items()}
        variant_hits = {name: target in ids for name, ids in candidates.items()}
        union_candidates = set().union(*candidates.values())
        hit_flags[sample_id] = {
            **variant_hits,
            "union": target in union_candidates,
        }

        matching_variants = [name for name, hit in variant_hits.items() if hit]
        if len(matching_variants) == 1:
            unique[matching_variants[0]] += 1

        for name in (*VARIANT_NAMES, "union"):
            if hit_flags[sample_id][name] or len(misses[name]) >= MISS_LIMIT:
                continue
            retrieved = sorted(union_candidates) if name == "union" else ranked[name]
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
            value = len(candidates[left] & candidates[right]) / len(union) if union else 0.0
            overlaps[f"{left}_{right}"].append(value)

    sample_count = len(samples)
    recall = {
        name: round(
            sum(hit_flags[str(sample["sample_id"])][name] for sample in samples)
            / sample_count,
            6,
        )
        for name in VARIANT_NAMES
    }
    pairwise_overlap = {
        name: round(statistics.fmean(values), 6) if values else 0.0
        for name, values in overlaps.items()
    }

    return {
        "depth": depth,
        "sample_count": sample_count,
        "queries_by_sample_id": queries_by_sample_id,
        "variant_recall_at_k": recall,
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
            name: round(build_times[name], 6) for name in VARIANT_NAMES
        },
        "mean_search_time_seconds": {
            name: round(statistics.fmean(search_times[name]), 6)
            for name in VARIANT_NAMES
        },
        "p95_search_time_seconds": {
            name: round(_p95(search_times[name]), 6) for name in VARIANT_NAMES
        },
        "scenario_recall_counts": _recall_counts(samples, hit_flags, "scenario_type"),
        "difficulty_recall_counts": _recall_counts(
            samples, hit_flags, "difficulty_bucket"
        ),
        "representative_misses": misses,
    }


def compare_dense_variants(
    samples: list[dict],
    products: dict[str, dict],
    categories: dict[str, list[str]],
    split: str,
    depths: list[int],
) -> dict:
    index = DenseVariantIndex(products)
    outcomes, search_times, queries_by_sample_id = execute_variants(
        samples,
        index,
        lambda sample: first_turn_query(sample, categories, products),
        max(depths),
    )
    return {
        "split": split,
        "depths": {
            str(depth): summarize_results(
                samples,
                outcomes,
                queries_by_sample_id,
                index.build_times,
                search_times,
                depth,
            )
            for depth in depths
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare TF-IDF and SVD dense variants on the fixed M3 split"
    )
    parser.add_argument(
        "--depth",
        type=int,
        nargs="+",
        required=True,
        help="one or more candidate depths summarized from the same retrieval run",
    )
    parser.add_argument("--catalog", default="data/catalog.jsonl")
    parser.add_argument("--dataset", default="data/public_set.jsonl")
    parser.add_argument("--output")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    depths = sorted(set(args.depth))
    if any(depth <= 0 for depth in depths):
        parser.error("--depth values must be positive")

    samples = load_jsonl(args.dataset)
    tuning, _ = stratified_split(samples)
    _, categories, products = catalog_index(args.catalog)
    result = compare_dense_variants(tuning, products, categories, "tuning", depths)
    output = json.dumps(result, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    print(output, end="")


if __name__ == "__main__":
    main()
