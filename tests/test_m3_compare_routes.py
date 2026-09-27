from __future__ import annotations

from collections import Counter
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from experiments.m3_compare_routes import (
    compare_routes,
    execute_routes,
    first_turn_query,
    stratified_split,
    summarize_results,
)
from starter.retrieval import RetrievalHit


ROOT = Path(__file__).resolve().parents[1]


class FakeRetriever:
    def __init__(self, parent_asin: str) -> None:
        self.parent_asin = parent_asin
        self.calls = []

    def search(self, query: str, depth: int) -> tuple[RetrievalHit, ...]:
        self.calls.append((query, depth))
        return (RetrievalHit(self.parent_asin, 1, 1.0),)


class M3CompareRoutesTest(unittest.TestCase):
    def test_compare_routes_builds_svd_256_with_256_dimensions(self) -> None:
        products = {"A": {"title": "hiking boots"}}

        with (
            patch("experiments.m3_compare_routes.LexicalRetriever"),
            patch("experiments.m3_compare_routes.FacetRetriever"),
            patch("experiments.m3_compare_routes.DenseRetriever") as dense,
            patch(
                "experiments.m3_compare_routes.execute_routes",
                return_value=({}, {}, {}),
            ) as execute,
            patch(
                "experiments.m3_compare_routes.summarize_results",
                return_value={},
            ),
        ):
            compare_routes([], products, {}, "tuning", 100)

        dense.assert_called_once_with(products, dimensions=256)
        retrievers = execute.call_args.args[1]
        self.assertIs(retrievers["svd_256"], dense.return_value)

    def test_stratified_split_is_deterministic_and_preserves_counts(self) -> None:
        scenario_counts = {
            "buying": 80,
            "browsing": 80,
            "intent_override": 30,
            "boundary": 10,
        }
        samples = [
            {"sample_id": f"{scenario}_{index}", "scenario_type": scenario}
            for scenario, count in scenario_counts.items()
            for index in range(count)
        ]

        tuning, holdout = stratified_split(samples)
        reversed_tuning, reversed_holdout = stratified_split(list(reversed(samples)))

        self.assertEqual(len(tuning), 160)
        self.assertEqual(len(holdout), 40)
        self.assertEqual(
            Counter(sample["scenario_type"] for sample in tuning),
            {"buying": 64, "browsing": 64, "intent_override": 24, "boundary": 8},
        )
        self.assertEqual(
            Counter(sample["scenario_type"] for sample in holdout),
            {"buying": 16, "browsing": 16, "intent_override": 6, "boundary": 2},
        )
        self.assertFalse(
            {sample["sample_id"] for sample in tuning}
            & {sample["sample_id"] for sample in holdout}
        )
        self.assertEqual(tuning, reversed_tuning)
        self.assertEqual(holdout, reversed_holdout)

    def test_first_turn_query_uses_evaluator_message_and_m2_parser(self) -> None:
        sample = {
            "sample_id": "one",
            "scenario_type": "buying",
            "ground_truth": {"parent_asin": "A"},
        }

        query = first_turn_query(
            sample,
            {"A": ["Clothing", "Hiking Shoes"]},
            {
                "A": {
                    "parent_asin": "A",
                    "title": "Trail Boots",
                    "features": ["waterproof"],
                }
            },
        )

        self.assertEqual(query, "Hiking Shoes waterproof")

    def test_every_route_receives_the_same_query_and_depth(self) -> None:
        samples = [{"sample_id": "one"}]
        retrievers = {
            "lexical": FakeRetriever("A"),
            "facet": FakeRetriever("B"),
            "svd_256": FakeRetriever("C"),
        }

        outcomes, _, queries_by_sample_id = execute_routes(
            samples, retrievers, lambda sample: "shared query", depth=7
        )

        for retriever in retrievers.values():
            self.assertEqual(retriever.calls, [("shared query", 7)])
        self.assertEqual(
            outcomes["one"],
            {"lexical": ["A"], "facet": ["B"], "svd_256": ["C"]},
        )
        self.assertEqual(queries_by_sample_id, {"one": "shared query"})

    def test_summarizes_synthetic_route_outcomes(self) -> None:
        samples = [
            {
                "sample_id": "s1",
                "scenario_type": "buying",
                "difficulty_bucket": "easy",
                "ground_truth": {"parent_asin": "A"},
            },
            {
                "sample_id": "s2",
                "scenario_type": "browsing",
                "difficulty_bucket": "hard",
                "ground_truth": {"parent_asin": "B"},
            },
            {
                "sample_id": "s3",
                "scenario_type": "boundary",
                "difficulty_bucket": "easy",
                "ground_truth": {"parent_asin": "C"},
            },
        ]
        outcomes = {
            "s1": {
                "lexical": ["A", "X"],
                "facet": ["X"],
                "svd_256": ["Y"],
            },
            "s2": {
                "lexical": ["Z"],
                "facet": ["B", "Z"],
                "svd_256": ["B"],
            },
            "s3": {
                "lexical": ["Q"],
                "facet": ["Q"],
                "svd_256": ["Q"],
            },
        }
        queries_by_sample_id = {
            "s1": "query one",
            "s2": "query two",
            "s3": "query three",
        }
        build_times = {"lexical": 1.0, "facet": 2.0, "svd_256": 3.0}
        search_times = {
            "lexical": [0.1, 0.2, 0.3],
            "facet": [0.2, 0.3, 0.4],
            "svd_256": [0.3, 0.4, 0.5],
        }

        result = summarize_results(
            samples,
            outcomes,
            queries_by_sample_id,
            build_times,
            search_times,
            "tuning",
            10,
        )

        self.assertEqual(result["queries_by_sample_id"], queries_by_sample_id)
        self.assertEqual(
            result["route_recall_at_k"],
            {"lexical": 0.333333, "facet": 0.333333, "svd_256": 0.333333},
        )
        self.assertEqual(result["union_recall_at_k"], 0.666667)
        self.assertEqual(
            result["unique_target_contribution"],
            {"lexical": 1, "facet": 0, "svd_256": 0},
        )
        self.assertEqual(
            result["mean_pairwise_jaccard_overlap"],
            {
                "lexical_facet": 0.666667,
                "lexical_svd_256": 0.333333,
                "facet_svd_256": 0.5,
                "overall": 0.5,
            },
        )
        self.assertEqual(
            result["scenario_recall_counts"]["lexical"]["buying"],
            {"hits": 1, "total": 1},
        )
        self.assertEqual(
            result["difficulty_recall_counts"]["union"]["easy"],
            {"hits": 1, "total": 2},
        )
        self.assertEqual(result["p95_search_time_seconds"]["svd_256"], 0.5)
        route_keys = {"lexical", "facet", "svd_256"}
        for section in (
            "build_time_seconds",
            "mean_search_time_seconds",
            "p95_search_time_seconds",
        ):
            self.assertEqual(set(result[section]), route_keys)
        for section in (
            "scenario_recall_counts",
            "difficulty_recall_counts",
            "representative_misses",
        ):
            self.assertEqual(set(result[section]), route_keys | {"union"})
        self.assertLessEqual(len(result["representative_misses"]["union"]), 5)
        for misses in result["representative_misses"].values():
            for miss in misses:
                self.assertEqual(
                    miss["query"], queries_by_sample_id[miss["sample_id"]]
                )

    def test_cli_help_lists_split_and_depth_without_loading_catalog(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "experiments.m3_compare_routes", "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--split {tuning,holdout}", result.stdout)
        self.assertIn("--depth", result.stdout)


if __name__ == "__main__":
    unittest.main()
