from __future__ import annotations

import argparse
import json

from benchmarking import BenchmarkConfig, run_benchmark


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a reproducible local benchmark with turn-level diagnostics."
    )
    parser.add_argument("--experiment", required=True, help="Short name for this configuration.")
    parser.add_argument(
        "--split",
        choices=("development", "lockbox", "all"),
        default="development",
        help="Deterministic public-data split to run.",
    )
    parser.add_argument("--sample-id", help="Run one public sample for debugging or replay.")
    parser.add_argument(
        "--sample-limit",
        type=int,
        help="Deterministically limit the selected split for a pilot run.",
    )
    parser.add_argument("--seed", type=int, default=42, help="Seed used to define the split.")
    parser.add_argument("--catalog", default="data/catalog.jsonl")
    parser.add_argument("--dataset", default="data/public_set.jsonl")
    parser.add_argument("--output-root", default="experiments/runs")
    parser.add_argument(
        "--agent-variant",
        choices=("always_10", "vague_3", "vague_0", "dynamic_safe"),
        default="always_10",
        help="Named clarification and recommendation policy to evaluate.",
    )
    parser.add_argument(
        "--retrieval-variant",
        choices=("single_bm25", "multi_route_rrf", "multi_route_structured"),
        default="multi_route_structured",
        help="Named lexical retrieval pipeline to evaluate.",
    )
    parser.add_argument(
        "--dense-variant",
        choices=(
            "dense_off",
            "dense_only",
            "hybrid_dense",
            "hybrid_dense_multi",
            "hybrid_dense_rescue",
            "hybrid_dense_profile",
            "hybrid_dense_v2",
            "hybrid_dense_fielded",
            "hybrid_dense_fielded_profile",
        ),
        default="dense_off",
        help="Named dense retrieval pipeline to evaluate.",
    )
    parser.add_argument(
        "--reranker-variant",
        choices=(
            "rerank_off",
            "minilm_l4_semantic",
            "minilm_l4_blended",
            "minilm_l4_fielded",
            "minilm_l4_constraint",
            "minilm_l4_guarded",
            "minilm_l4_route_aware",
            "minilm_l4_constraint_legacy",
            "minilm_l4_bounded",
            "minilm_l6_blended",
        ),
        default="minilm_l4_blended",
        help="Named semantic reranker to evaluate.",
    )
    parser.add_argument("--reranker-depth", type=int, default=60)
    parser.add_argument("--reranker-batch-size", type=int, default=32)
    parser.add_argument("--reranker-semantic-weight", type=float, default=0.25)
    parser.add_argument(
        "--orchestration-variant",
        choices=(
            "static",
            "static_shadow",
            "adaptive_rerank",
            "adaptive_cutoff",
            "adaptive_recovery",
            "adaptive_full",
        ),
        default="adaptive_cutoff",
        help="Named deterministic per-turn orchestration strategy to evaluate.",
    )
    parser.add_argument(
        "--allow-lockbox",
        action="store_true",
        help="Required to intentionally run the reserved lockbox split.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.split == "lockbox" and not args.allow_lockbox and not args.sample_id:
        raise SystemExit("Refusing to run the lockbox without --allow-lockbox.")

    config = BenchmarkConfig(
        experiment_name=args.experiment,
        catalog_path=args.catalog,
        dataset_path=args.dataset,
        output_root=args.output_root,
        split=args.split,
        seed=args.seed,
        sample_id=args.sample_id,
        sample_limit=args.sample_limit,
        agent_variant=args.agent_variant,
        retrieval_variant=args.retrieval_variant,
        dense_variant=args.dense_variant,
        reranker_variant=args.reranker_variant,
        reranker_depth=args.reranker_depth,
        reranker_batch_size=args.reranker_batch_size,
        reranker_semantic_weight=args.reranker_semantic_weight,
        orchestration_variant=args.orchestration_variant,
    )
    summary, run_directory = run_benchmark(config)
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"Artifacts: {run_directory}")


if __name__ == "__main__":
    main()
