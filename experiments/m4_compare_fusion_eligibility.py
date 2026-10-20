from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import json
from pathlib import Path
import platform
import shlex
import statistics

import sklearn

from evaluator.local_evaluator import (
    catalog_index,
    coarse_category,
    initial_message,
    load_jsonl,
    materialize_hidden_fields,
)
from experiments.m3_compare_routes import ROUTE_NAMES
from experiments.prepare_m4_split import SPLIT_ID, sha256_file
from starter.constraint_comparison import assess_candidate_constraints
from starter.dense_retrieval import DenseRetriever
from starter.eligibility import (
    AssessmentState,
    EligibilityResult,
    EligibilityStatus,
    partition_candidate_eligibility,
)
from starter.facet_retrieval import FacetRetriever
from starter.fusion import FusedCandidate, apply_candidate_budget, fuse_candidates
from starter.intent import ObservedClaim, parse_intent
from starter.lexical_retrieval import LexicalRetriever
from starter.retrieval import RetrievalHit, build_retrieval_query


ROUTE_DEPTH = 100
RRF_RANK_CONSTANT = 60
CANONICAL_SOURCE_PATH = Path("data/public_set.jsonl")
CANONICAL_TUNING_PATH = Path("data/m4_tuning.jsonl")
CANONICAL_HOLDOUT_PATH = Path("secure/m4_holdout.jsonl")
CANONICAL_MANIFEST_PATH = Path("data/m4_split_manifest.json")
CANONICAL_SPLIT_PATHS = (
    CANONICAL_SOURCE_PATH,
    CANONICAL_TUNING_PATH,
    CANONICAL_HOLDOUT_PATH,
)


@dataclass(frozen=True)
class PreparedMessage:
    sample_id: str
    message: str


@dataclass(frozen=True)
class ScoringLabel:
    sample_id: str
    target_parent_asin: str


def prepare_tuning_session(
    sample: dict,
    categories: dict[str, list[str]],
    products: dict[str, dict],
) -> tuple[PreparedMessage, ScoringLabel]:
    """Use trusted simulator data only to prepare a message and scoring label."""
    target = str(sample["ground_truth"]["parent_asin"])
    intent_card, behavior = materialize_hidden_fields(sample, products)
    simulator_sample = {**sample, "intent_card": intent_card, "behavior": behavior}
    message = initial_message(
        simulator_sample,
        coarse_category(categories[target]),
        set(),
    )
    sample_id = str(sample["sample_id"])
    return PreparedMessage(sample_id, message), ScoringLabel(sample_id, target)


def execute_routes(
    query: str,
    retrievers: dict[str, object],
    depth: int,
) -> dict[str, tuple[RetrievalHit, ...]]:
    """Run every provisional M3 route with one shared query and depth."""
    return {
        name: retrievers[name].search(query, depth)
        for name in ROUTE_NAMES
    }


def evaluate_cutoffs(
    route_hits: dict[str, tuple[RetrievalHit, ...]],
    products: dict[str, dict],
    claims: tuple[ObservedClaim, ...],
    cutoffs: tuple[int, ...],
) -> tuple[
    tuple[FusedCandidate, ...],
    dict[int, dict[str, tuple[EligibilityResult, ...]]],
]:
    """Fuse once, then assess and partition candidates at every cutoff."""
    fused = fuse_candidates(route_hits)
    evaluations = {}
    for cutoff in cutoffs:
        candidates = apply_candidate_budget(fused, cutoff)
        results = tuple(
            assess_candidate_constraints(
                candidate,
                products[candidate.parent_asin],
                claims,
            )
            for candidate in candidates
        )
        retained, excluded = partition_candidate_eligibility(results)
        evaluations[cutoff] = {
            "results": results,
            "retained": retained,
            "excluded": excluded,
        }
    return fused, evaluations


def process_prepared_message(
    prepared: PreparedMessage,
    products: dict[str, dict],
    retrievers: dict[str, object],
    cutoffs: tuple[int, ...],
    depth: int,
) -> dict:
    """Run retrieval and eligibility from a prepared message without labels."""
    claims = parse_intent(prepared.message).claims
    query = build_retrieval_query(claims)
    route_hits = execute_routes(query, retrievers, depth)
    fused, evaluations = evaluate_cutoffs(route_hits, products, claims, cutoffs)
    return {
        "sample_id": prepared.sample_id,
        "message": prepared.message,
        "query": query,
        "route_hits": route_hits,
        "fused": fused,
        "evaluations": evaluations,
    }


def _target_rank(target: str, candidates) -> int | None:
    for rank, candidate in enumerate(candidates, start=1):
        parent_asin = getattr(candidate, "parent_asin", candidate)
        if parent_asin == target:
            return rank
    return None


def _excluded_evidence(
    results: tuple[EligibilityResult, ...],
) -> list[dict[str, object]]:
    return [
        {
            "parent_asin": result.candidate.parent_asin,
            "contradiction_reasons": [
                assessment.reason
                for assessment in result.assessments
                if assessment.state is AssessmentState.CONFIRMED_CONTRADICTION
            ],
        }
        for result in results
    ]


def summarize_session(
    label: ScoringLabel,
    processed: dict,
) -> dict:
    """Use the target label only after retrieval and eligibility are complete."""
    target = label.target_parent_asin
    route_hits = processed["route_hits"]
    fused = processed["fused"]
    evaluations = processed["evaluations"]
    cutoff_summaries = {}

    for cutoff, evaluation in evaluations.items():
        results = evaluation["results"]
        retained = evaluation["retained"]
        excluded = evaluation["excluded"]
        target_result = next(
            (result for result in results if result.candidate.parent_asin == target),
            None,
        )
        status_counts = Counter(result.status.value for result in results)
        contradiction_leakage = sum(
            any(
                assessment.state is AssessmentState.CONFIRMED_CONTRADICTION
                for assessment in result.assessments
            )
            for result in retained
        )
        cutoff_summaries[str(cutoff)] = {
            "candidate_count": len(results),
            "confirmed_count": status_counts[EligibilityStatus.CONFIRMED.value],
            "provisional_count": status_counts[EligibilityStatus.PROVISIONAL.value],
            "ineligible_count": status_counts[EligibilityStatus.INELIGIBLE.value],
            "retained_count": len(retained),
            "target_present": target_result is not None,
            "target_retained": target_result in retained,
            "false_exclusion_count": int(
                target_result is not None
                and target_result.status is EligibilityStatus.INELIGIBLE
            ),
            "contradiction_leakage_count": contradiction_leakage,
            "excluded": _excluded_evidence(excluded),
        }

    return {
        "sample_id": processed["sample_id"],
        "message": processed["message"],
        "query": processed["query"],
        "target_parent_asin": target,
        "route_target_ranks": {
            name: next(
                (hit.rank for hit in route_hits[name] if hit.parent_asin == target),
                None,
            )
            for name in ROUTE_NAMES
        },
        "full_union_contains_target": any(
            hit.parent_asin == target
            for hits in route_hits.values()
            for hit in hits
        ),
        "fused_target_rank": _target_rank(target, fused),
        "cutoffs": cutoff_summaries,
    }


def build_report(
    sessions: list[dict],
    cutoffs: tuple[int, ...],
    depth: int,
    reproducibility: dict | None = None,
) -> dict:
    sample_count = len(sessions)
    cutoff_metrics = {}
    for cutoff in cutoffs:
        key = str(cutoff)
        summaries = [session["cutoffs"][key] for session in sessions]
        sample_count = len(summaries)
        cutoff_metrics[key] = {
            "target_recall": round(
                sum(summary["target_present"] for summary in summaries)
                / sample_count,
                6,
            ) if sample_count else 0.0,
            "targets_lost_relative_to_full_union": sum(
                session["full_union_contains_target"]
                and not session["cutoffs"][key]["target_present"]
                for session in sessions
            ),
            "mean_candidate_count": round(
                statistics.fmean(
                    summary["candidate_count"] for summary in summaries
                ),
                6,
            ) if summaries else 0.0,
            "mean_retained_candidate_count": round(
                statistics.fmean(
                    summary["retained_count"] for summary in summaries
                ),
                6,
            ) if summaries else 0.0,
            "confirmed_count": sum(summary["confirmed_count"] for summary in summaries),
            "provisional_count": sum(summary["provisional_count"] for summary in summaries),
            "ineligible_count": sum(summary["ineligible_count"] for summary in summaries),
            "retained_count": sum(summary["retained_count"] for summary in summaries),
            "false_exclusion_count": sum(
                summary["false_exclusion_count"] for summary in summaries
            ),
            "contradiction_leakage_count": sum(
                summary["contradiction_leakage_count"] for summary in summaries
            ),
        }

    report = {
        "split": "tuning",
        "sample_count": sample_count,
        "route_depth": depth,
        "route_names": list(ROUTE_NAMES),
        "route_target_recall": {
            name: round(
                sum(session["route_target_ranks"][name] is not None for session in sessions)
                / sample_count,
                6,
            ) if sample_count else 0.0
            for name in ROUTE_NAMES
        },
        "full_union_target_recall": round(
            sum(session["full_union_contains_target"] for session in sessions)
            / sample_count,
            6,
        ) if sample_count else 0.0,
        "cutoffs": cutoff_metrics,
        "sessions": sessions,
    }
    if reproducibility is not None:
        report["reproducibility"] = reproducibility
    return report


def validate_split_manifest(
    manifest: dict,
    expected_paths: tuple[Path, Path, Path] = CANONICAL_SPLIT_PATHS,
) -> dict:
    if manifest["split_id"] != SPLIT_ID:
        raise ValueError(f"split manifest must use accepted split identity {SPLIT_ID}")

    source = manifest["source"]
    expected = manifest["partitions"]["tuning"]
    holdout = manifest["partitions"]["holdout"]
    paths = tuple(Path(item["path"]) for item in (source, expected, holdout))
    if paths != expected_paths:
        raise ValueError(
            "split manifest must declare the canonical source, tuning, and holdout paths"
        )
    if len(set(paths)) != 3:
        raise ValueError("source, tuning, and holdout paths must be distinct")

    hashes = [item["sha256"] for item in (source, expected, holdout)]
    if len(set(hashes)) != 3:
        raise ValueError("source, tuning, and holdout SHA-256 hashes must be distinct")
    if set(expected["sample_ids"]) & set(holdout["sample_ids"]):
        raise ValueError("tuning and holdout sample IDs must not overlap")
    return expected


def load_prepared_tuning(
    tuning_path: Path = CANONICAL_TUNING_PATH,
    manifest_path: Path = CANONICAL_MANIFEST_PATH,
    expected_paths: tuple[Path, Path, Path] = CANONICAL_SPLIT_PATHS,
) -> tuple[list[dict], dict]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = validate_split_manifest(manifest, expected_paths)

    actual_hash = sha256_file(tuning_path)
    if actual_hash != expected["sha256"]:
        raise ValueError("prepared tuning file SHA-256 does not match split manifest")

    samples = load_jsonl(tuning_path)
    sample_ids = [str(sample["sample_id"]) for sample in samples]
    if sample_ids != expected["sample_ids"]:
        raise ValueError("prepared tuning sample IDs do not match split manifest")
    if len(samples) != expected["sample_count"]:
        raise ValueError("prepared tuning sample count does not match split manifest")
    return samples, manifest


def build_reproducibility_manifest(
    split_manifest: dict,
    tuning_path: Path,
    catalog_path: Path,
    cutoffs: tuple[int, ...],
    command: str,
    depth: int = ROUTE_DEPTH,
) -> dict:
    return {
        "split": {
            "split_id": split_manifest["split_id"],
            "method": split_manifest["method"],
            "seed_statement": split_manifest["seed_statement"],
            "source": split_manifest["source"],
            "partitions": split_manifest["partitions"],
        },
        "inputs": {
            "catalog": {"path": str(catalog_path), "sha256": sha256_file(catalog_path)},
            "tuning": {"path": str(tuning_path), "sha256": sha256_file(tuning_path)},
        },
        "command": command,
        "environment": {
            "python": platform.python_version(),
            "scikit_learn": sklearn.__version__,
        },
        "configuration": {
            "route_names": list(ROUTE_NAMES),
            "route_depth": depth,
            "fusion": "reciprocal_rank_fusion",
            "rrf_rank_constant": RRF_RANK_CONSTANT,
            "cutoffs": list(cutoffs),
        },
    }


def compare_fusion_eligibility(
    samples: list[dict],
    products: dict[str, dict],
    categories: dict[str, list[str]],
    cutoffs: tuple[int, ...],
    depth: int = ROUTE_DEPTH,
) -> dict:
    retrievers = {
        "lexical": LexicalRetriever(products),
        "facet": FacetRetriever(products),
        "svd_256": DenseRetriever(products, dimensions=256),
    }
    sessions = []
    for sample in samples:
        prepared, label = prepare_tuning_session(sample, categories, products)
        processed = process_prepared_message(
            prepared,
            products,
            retrievers,
            cutoffs,
            depth,
        )
        sessions.append(summarize_session(label, processed))
    return build_report(sessions, cutoffs, depth)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare the tuning-only M4 fusion, cutoff, and eligibility report; "
            "reads canonical data/m4_tuning.jsonl and data/m4_split_manifest.json; "
            "never evaluates the holdout or selects a cutoff"
        )
    )
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--cutoffs", type=int, nargs="+", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    cutoffs = tuple(sorted(set(args.cutoffs)))
    if any(cutoff <= 0 for cutoff in cutoffs):
        parser.error("--cutoffs values must be positive")

    catalog_path = Path(args.catalog)
    try:
        tuning, split_manifest = load_prepared_tuning()
    except (KeyError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))

    _, categories, products = catalog_index(args.catalog)
    report = compare_fusion_eligibility(tuning, products, categories, cutoffs)
    command = shlex.join(
        [
            "uv", "run", "--python", "3.12", "python", "-m",
            "experiments.m4_compare_fusion_eligibility",
            "--catalog", args.catalog,
            "--cutoffs", *(str(cutoff) for cutoff in cutoffs),
            "--output", args.output,
        ]
    )
    report["reproducibility"] = build_reproducibility_manifest(
        split_manifest,
        CANONICAL_TUNING_PATH,
        catalog_path,
        cutoffs,
        command,
    )
    output = json.dumps(report, indent=2) + "\n"
    Path(args.output).write_text(output, encoding="utf-8")
    print(output, end="")


if __name__ == "__main__":
    main()
