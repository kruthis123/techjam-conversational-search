from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from experiments.m4_compare_fusion_eligibility import (
    CANONICAL_HOLDOUT_PATH,
    CANONICAL_SOURCE_PATH,
    CANONICAL_TUNING_PATH,
    PreparedMessage,
    ScoringLabel,
    build_report,
    build_reproducibility_manifest,
    evaluate_cutoffs,
    execute_routes,
    load_prepared_tuning,
    prepare_tuning_session,
    process_prepared_message,
    summarize_session,
    validate_split_manifest,
)
from experiments.prepare_m4_split import SPLIT_ID, sha256_file
from starter.intent import ObservedClaim
from starter.retrieval import RetrievalHit


ROOT = Path(__file__).resolve().parents[1]


class FakeRetriever:
    def __init__(self, hits: tuple[RetrievalHit, ...]) -> None:
        self.hits = hits
        self.calls = []

    def search(self, query: str, depth: int) -> tuple[RetrievalHit, ...]:
        self.calls.append((query, depth))
        return self.hits


class M4CompareFusionEligibilityTest(unittest.TestCase):
    def test_every_route_receives_the_same_query_and_depth(self) -> None:
        retrievers = {
            "lexical": FakeRetriever((RetrievalHit("A", 1, 3.0),)),
            "facet": FakeRetriever((RetrievalHit("B", 1, 2.0),)),
            "svd_256": FakeRetriever((RetrievalHit("C", 1, 1.0),)),
        }

        outcomes = execute_routes("shared query", retrievers, depth=100)

        for retriever in retrievers.values():
            self.assertEqual(retriever.calls, [("shared query", 100)])
        self.assertEqual(tuple(outcomes), ("lexical", "facet", "svd_256"))

    def test_complete_path_separates_message_processing_from_target_scoring(self) -> None:
        products = {
            "TARGET": {
                "parent_asin": "TARGET",
                "title": "Waterproof hiking shoes",
                "features": ["waterproof"],
            }
        }
        prepared, label = prepare_tuning_session(
            {
                "sample_id": "s1",
                "scenario_type": "buying",
                "ground_truth": {"parent_asin": "TARGET"},
                "intent_card": {
                    "hard_constraints": ["waterproof"],
                    "soft_preferences": [],
                },
                "behavior": {},
            },
            {"TARGET": ["Clothing", "Hiking Shoes"]},
            products,
        )
        retrievers = {
            name: FakeRetriever((RetrievalHit("TARGET", 1, 1.0),))
            for name in ("lexical", "facet", "svd_256")
        }

        processed = process_prepared_message(
            prepared,
            products,
            retrievers,
            (1,),
            100,
        )

        self.assertIsInstance(prepared, PreparedMessage)
        self.assertFalse(hasattr(prepared, "target_parent_asin"))
        self.assertEqual(processed["query"], "Hiking Shoes waterproof")
        self.assertNotIn("target_parent_asin", processed)
        for retriever in retrievers.values():
            self.assertEqual(
                retriever.calls,
                [("Hiking Shoes waterproof", 100)],
            )

        session = summarize_session(label, processed)
        self.assertIsInstance(label, ScoringLabel)
        self.assertEqual(session["target_parent_asin"], "TARGET")
        self.assertTrue(session["cutoffs"]["1"]["target_retained"])

    def test_records_route_union_fusion_and_cutoff_target_evidence(self) -> None:
        route_hits = {
            "lexical": (
                RetrievalHit("SHARED", 1, 3.0),
                RetrievalHit("TARGET", 2, 2.0),
            ),
            "facet": (RetrievalHit("SHARED", 1, 2.0),),
            "svd_256": (RetrievalHit("SVD", 1, 1.0),),
        }
        products = {
            parent_asin: {"parent_asin": parent_asin}
            for parent_asin in ("SHARED", "TARGET", "SVD")
        }
        fused, evaluations = evaluate_cutoffs(route_hits, products, (), (2, 3))

        session = summarize_session(
            ScoringLabel("s1", "TARGET"),
            {
                "sample_id": "s1",
                "message": "message",
                "query": "shared query",
                "route_hits": route_hits,
                "fused": fused,
                "evaluations": evaluations,
            },
        )
        report = build_report([session], (2, 3), 100)

        self.assertEqual(
            session["route_target_ranks"],
            {"lexical": 2, "facet": None, "svd_256": None},
        )
        self.assertTrue(session["full_union_contains_target"])
        self.assertEqual(session["fused_target_rank"], 3)
        self.assertFalse(session["cutoffs"]["2"]["target_present"])
        self.assertTrue(session["cutoffs"]["3"]["target_present"])
        self.assertEqual(report["cutoffs"]["2"]["target_recall"], 0.0)
        self.assertEqual(report["sample_count"], 1)
        self.assertEqual(
            report["route_target_recall"],
            {"lexical": 1.0, "facet": 0.0, "svd_256": 0.0},
        )
        self.assertEqual(report["full_union_target_recall"], 1.0)
        self.assertEqual(
            report["cutoffs"]["2"]["targets_lost_relative_to_full_union"],
            1,
        )
        self.assertEqual(report["cutoffs"]["2"]["mean_candidate_count"], 2.0)
        self.assertEqual(
            report["cutoffs"]["2"]["mean_retained_candidate_count"],
            2.0,
        )

    def test_summarizes_eligibility_and_false_exclusion_evidence(self) -> None:
        route_hits = {
            "lexical": (
                RetrievalHit("CONFIRMED", 1, 3.0),
                RetrievalHit("PROVISIONAL", 2, 2.0),
                RetrievalHit("TARGET", 3, 1.0),
            ),
            "facet": (),
            "svd_256": (),
        }
        products = {
            "CONFIRMED": {
                "parent_asin": "CONFIRMED",
                "features": ["water resistant"],
                "price": 70,
            },
            "PROVISIONAL": {
                "parent_asin": "PROVISIONAL",
                "price": 70,
            },
            "TARGET": {
                "parent_asin": "TARGET",
                "features": ["water resistant"],
                "price": 80,
            },
        }
        claims = (
            ObservedClaim("feature", "water resistant", "required"),
            ObservedClaim("budget", "under $80", "required"),
        )
        fused, evaluations = evaluate_cutoffs(route_hits, products, claims, (3,))

        session = summarize_session(
            ScoringLabel("s1", "TARGET"),
            {
                "sample_id": "s1",
                "message": "message",
                "query": "water resistant under 80",
                "route_hits": route_hits,
                "fused": fused,
                "evaluations": evaluations,
            },
        )
        summary = build_report([session], (3,), 100)["cutoffs"]["3"]

        self.assertEqual(summary["confirmed_count"], 1)
        self.assertEqual(summary["provisional_count"], 1)
        self.assertEqual(summary["ineligible_count"], 1)
        self.assertEqual(summary["retained_count"], 2)
        self.assertEqual(summary["mean_retained_candidate_count"], 2.0)
        self.assertEqual(summary["false_exclusion_count"], 1)
        self.assertEqual(summary["contradiction_leakage_count"], 0)
        exclusion = session["cutoffs"]["3"]["excluded"][0]
        self.assertEqual(exclusion["parent_asin"], "TARGET")
        self.assertIn("price", exclusion["contradiction_reasons"][0])

    def test_empty_route_outputs_produce_zero_counts(self) -> None:
        route_hits = {"lexical": (), "facet": (), "svd_256": ()}
        fused, evaluations = evaluate_cutoffs(route_hits, {}, (), (25,))

        session = summarize_session(
            ScoringLabel("s1", "TARGET"),
            {
                "sample_id": "s1",
                "message": "message",
                "query": "query",
                "route_hits": route_hits,
                "fused": fused,
                "evaluations": evaluations,
            },
        )
        summary = build_report([session], (25,), 100)["cutoffs"]["25"]

        self.assertFalse(session["full_union_contains_target"])
        self.assertIsNone(session["fused_target_rank"])
        self.assertEqual(summary["target_recall"], 0.0)
        self.assertEqual(summary["mean_candidate_count"], 0.0)
        self.assertEqual(summary["mean_retained_candidate_count"], 0.0)
        self.assertEqual(summary["retained_count"], 0)

    def test_cli_help_documents_tuning_only_required_inputs(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "experiments.m4_compare_fusion_eligibility",
                "--help",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        help_text = " ".join(result.stdout.split())
        self.assertIn("tuning-only", help_text)
        self.assertIn("never evaluates the holdout", help_text)
        self.assertIn("data/m4_tuning.jsonl", help_text)
        self.assertIn("data/m4_split_manifest.json", help_text)
        for argument in ("--catalog", "--cutoffs", "--output"):
            self.assertIn(argument, result.stdout)
        self.assertNotIn("--tuning", result.stdout)
        self.assertNotIn("--manifest", result.stdout)

    def test_prepared_tuning_must_match_manifest_before_catalog_loading(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            tuning = root / "tuning.jsonl"
            tuning.write_text('{"sample_id":"s1"}\n', encoding="utf-8")
            manifest = {
                "split_id": SPLIT_ID,
                "source": {
                    "path": str(root / "public.jsonl"),
                    "sha256": "source-hash",
                },
                "partitions": {
                    "tuning": {
                        "path": str(tuning),
                        "sample_count": 1,
                        "sample_ids": ["s1"],
                        "sha256": sha256_file(tuning),
                    },
                    "holdout": {
                        "path": str(root / "holdout.jsonl"),
                        "sample_count": 1,
                        "sample_ids": ["s2"],
                        "sha256": "holdout-hash",
                    },
                },
            }
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            expected_paths = (
                root / "public.jsonl",
                tuning,
                root / "holdout.jsonl",
            )

            samples, loaded_manifest = load_prepared_tuning(
                tuning,
                manifest_path,
                expected_paths,
            )
            self.assertEqual(samples, [{"sample_id": "s1"}])
            self.assertEqual(loaded_manifest, manifest)

            tuning.write_text('{"sample_id":"changed"}\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                load_prepared_tuning(tuning, manifest_path, expected_paths)

    def test_manifest_cannot_relabel_source_or_holdout_as_tuning(self) -> None:
        manifest = {
            "split_id": SPLIT_ID,
            "source": {"path": str(CANONICAL_SOURCE_PATH), "sha256": "source-hash"},
            "partitions": {
                "tuning": {
                    "path": str(CANONICAL_TUNING_PATH),
                    "sample_ids": ["tuning-id"],
                    "sha256": "tuning-hash",
                },
                "holdout": {
                    "path": str(CANONICAL_HOLDOUT_PATH),
                    "sample_ids": ["holdout-id"],
                    "sha256": "holdout-hash",
                },
            },
        }

        for relabelled in (CANONICAL_SOURCE_PATH, CANONICAL_HOLDOUT_PATH):
            changed = json.loads(json.dumps(manifest))
            old_tuning = changed["partitions"]["tuning"]["path"]
            if relabelled == CANONICAL_SOURCE_PATH:
                changed["source"]["path"] = old_tuning
            else:
                changed["partitions"]["holdout"]["path"] = old_tuning
            changed["partitions"]["tuning"]["path"] = str(relabelled)

            with self.subTest(tuning=str(relabelled)), self.assertRaisesRegex(
                ValueError,
                "canonical source, tuning, and holdout paths",
            ):
                validate_split_manifest(changed)

    def test_manifest_rejects_overlapping_partition_ids_before_reading_tuning(self) -> None:
        manifest = {
            "split_id": SPLIT_ID,
            "source": {"path": "source.jsonl", "sha256": "source-hash"},
            "partitions": {
                "tuning": {
                    "path": "tuning.jsonl",
                    "sample_ids": ["shared"],
                    "sha256": "tuning-hash",
                },
                "holdout": {
                    "path": "holdout.jsonl",
                    "sample_ids": ["shared"],
                    "sha256": "holdout-hash",
                },
            },
        }

        with self.assertRaisesRegex(ValueError, "must not overlap"):
            validate_split_manifest(
                manifest,
                (Path("source.jsonl"), Path("tuning.jsonl"), Path("holdout.jsonl")),
            )

    def test_synthetic_report_manifest_records_reproducibility_fields(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            tuning = root / "tuning.jsonl"
            catalog = root / "catalog.jsonl"
            tuning.write_text('{"sample_id":"s1"}\n', encoding="utf-8")
            catalog.write_text('{"parent_asin":"A"}\n', encoding="utf-8")
            split_manifest = {
                "split_id": "split-v1",
                "method": "deterministic method",
                "seed_statement": "No random seed.",
                "source": {"path": "source.jsonl", "sha256": "source-hash"},
                "partitions": {
                    "tuning": {"sample_ids": ["s1"], "sha256": sha256_file(tuning)},
                    "holdout": {"sample_ids": ["s2"], "sha256": "holdout-hash"},
                },
            }

            with patch("platform.python_version", return_value="3.12.test"), patch(
                "sklearn.__version__", "1.test"
            ):
                reproducibility = build_reproducibility_manifest(
                    split_manifest,
                    tuning,
                    catalog,
                    (25, 50),
                    "exact command",
                )
            report = build_report([], (25, 50), 100, reproducibility)

            self.assertEqual(report["reproducibility"]["split"]["split_id"], "split-v1")
            self.assertEqual(
                report["reproducibility"]["split"]["partitions"]["holdout"]["sample_ids"],
                ["s2"],
            )
            self.assertEqual(
                report["reproducibility"]["inputs"]["catalog"]["sha256"],
                sha256_file(catalog),
            )
            self.assertEqual(report["reproducibility"]["command"], "exact command")
            self.assertEqual(
                report["reproducibility"]["environment"],
                {"python": "3.12.test", "scikit_learn": "1.test"},
            )
            self.assertEqual(
                report["reproducibility"]["configuration"]["rrf_rank_constant"],
                60,
            )


if __name__ == "__main__":
    unittest.main()
