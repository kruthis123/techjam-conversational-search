from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import unittest

from experiments.m3_compare_dense_variants import (
    DenseVariantIndex,
    execute_variants,
    summarize_results,
)
from starter.dense_retrieval import DenseRetriever
from starter.retrieval import RetrievalHit


ROOT = Path(__file__).resolve().parents[1]


class FakeTimedIndex:
    def search_with_timings(self, query: str, depth: int):
        hits = {
            name: (RetrievalHit(name, 1, 1.0),)
            for name in ("raw_tfidf", "svd_64", "svd_256")
        }
        timings = {"raw_tfidf": 0.1, "svd_64": 0.2, "svd_256": 0.3}
        return hits, timings


class M3CompareDenseVariantsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.products = {
            "A": {"title": "red wool hiking coat", "categories": ["coats"]},
            "B": {"title": "blue cotton summer shirt", "categories": ["shirts"]},
            "C": {"title": "black leather trail boots", "categories": ["shoes"]},
        }

    def test_svd_64_matches_current_dense_baseline(self) -> None:
        comparison = DenseVariantIndex(self.products)
        baseline = DenseRetriever(self.products)

        expected = baseline.search("leather trail", 3)
        actual = comparison.search("leather trail", 3)["svd_64"]

        self.assertEqual(
            [hit.parent_asin for hit in actual],
            [hit.parent_asin for hit in expected],
        )
        self.assertEqual(comparison.parent_asins, tuple(self.products))
        self.assertEqual(comparison.vectorizer.vocabulary_, baseline._vectorizer.vocabulary_)

    def test_all_variants_receive_one_query_and_maximum_depth(self) -> None:
        index = DenseVariantIndex(self.products)
        outcomes, search_times, queries = execute_variants(
            [{"sample_id": "one"}],
            index,
            lambda sample: "hiking coat",
            depth=3,
        )

        self.assertEqual(queries, {"one": "hiking coat"})
        self.assertEqual(set(outcomes["one"]), {"raw_tfidf", "svd_64", "svd_256"})
        self.assertTrue(all(len(ids) == 3 for ids in outcomes["one"].values()))
        self.assertTrue(all(len(values) == 1 for values in search_times.values()))

    def test_execute_variants_keeps_distinct_per_variant_timings(self) -> None:
        _, search_times, _ = execute_variants(
            [{"sample_id": "one"}],
            FakeTimedIndex(),
            lambda sample: "shared query",
            depth=100,
        )

        self.assertEqual(
            search_times,
            {"raw_tfidf": [0.1], "svd_64": [0.2], "svd_256": [0.3]},
        )

    def test_multiple_depths_are_summarized_from_the_same_outcomes(self) -> None:
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
        ]
        outcomes = {
            "s1": {
                "raw_tfidf": ["A", "X"],
                "svd_64": ["X", "A"],
                "svd_256": ["X", "Y"],
            },
            "s2": {
                "raw_tfidf": ["X", "B"],
                "svd_64": ["X", "Y"],
                "svd_256": ["B", "X"],
            },
        }
        queries = {"s1": "query one", "s2": "query two"}
        build_times = {name: 1.0 for name in ("raw_tfidf", "svd_64", "svd_256")}
        search_times = {name: [0.1, 0.2] for name in build_times}

        at_one = summarize_results(
            samples, outcomes, queries, build_times, search_times, depth=1
        )
        at_two = summarize_results(
            samples, outcomes, queries, build_times, search_times, depth=2
        )

        self.assertEqual(
            at_one["variant_recall_at_k"],
            {"raw_tfidf": 0.5, "svd_64": 0.0, "svd_256": 0.5},
        )
        self.assertEqual(
            at_two["variant_recall_at_k"],
            {"raw_tfidf": 1.0, "svd_64": 0.5, "svd_256": 0.5},
        )
        self.assertEqual(at_one["union_recall_at_k"], 1.0)
        self.assertEqual(
            at_one["unique_target_contribution"],
            {"raw_tfidf": 1, "svd_64": 0, "svd_256": 1},
        )
        self.assertEqual(
            at_one["scenario_recall_counts"]["raw_tfidf"]["buying"],
            {"hits": 1, "total": 1},
        )
        self.assertEqual(
            at_one["difficulty_recall_counts"]["union"]["hard"],
            {"hits": 1, "total": 1},
        )
        self.assertLessEqual(len(at_one["representative_misses"]["svd_64"]), 5)
        self.assertIn("mean_pairwise_jaccard_overlap", at_one)
        self.assertIn("build_time_seconds", at_one)
        self.assertIn("mean_search_time_seconds", at_one)
        self.assertIn("p95_search_time_seconds", at_one)

    def test_cli_help_explains_inputs_without_loading_data(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "experiments.m3_compare_dense_variants",
                "--help",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--depth DEPTH [DEPTH ...]", result.stdout)
        self.assertIn("--catalog", result.stdout)
        self.assertIn("--dataset", result.stdout)
        self.assertRegex(result.stdout, r"same\s+retrieval run")


if __name__ == "__main__":
    unittest.main()
