from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from benchmarking.models import BenchmarkConfig
from benchmarking.runner import run_benchmark, select_samples, validate_response
from evaluator.local_evaluator import catalog_index, evaluate


class StaticAgent:
    def __init__(self, catalog_path: str) -> None:
        self.sessions: set[str] = set()

    def reset(self, session_id: str, user_profile: dict) -> None:
        self.sessions.add(session_id)

    def respond(self, session_id: str, user_message: str, turn: int, top_k: int) -> dict:
        if session_id not in self.sessions:
            raise RuntimeError("reset was not called")
        return {
            "message": "Here is one result.",
            "ask_attribute": "feature",
            "recommendations": [{"parent_asin": "A"}],
        }


class TracedAgent(StaticAgent):
    def get_last_trace(self, session_id: str) -> dict:
        return {
            "candidate_ids": ["B", "A"],
            "inferred_route": "buying",
            "recommendation_limit": 1,
            "confidence": 0.5,
            "intent_confidence": 0.7,
            "recommendation_confidence": 0.5,
            "confidence_components": {"intent": 0.7},
            "clarification_utility": 0.8,
            "policy_reasons": ["test"],
            "retrieval_name": "test_retrieval",
            "route_candidate_ids": {
                "current_message": ["B", "A"],
                "category": ["A", "B"],
            },
            "compiled_queries": {"current_message": ["shoe"]},
            "candidate_evidence": [{"parent_asin": "A", "fused_score": 1.0}],
            "orchestration": {
                "shadow": False,
                "fallback_reason": None,
                "proposed_plan": {
                    "mode": "precision",
                    "reranker_enabled": True,
                },
                "executed_plan": {
                    "mode": "precision",
                    "reranker_enabled": True,
                    "rerank_depth": 60,
                },
            },
            "orchestration_signals": {"route": "buying"},
        }


class DenseViewTracedAgent(StaticAgent):
    def get_last_trace(self, session_id: str) -> dict:
        return {
            "candidate_ids": ["A", "B"],
            "route_candidate_ids": {
                "current_message": ["B"],
                "dense": ["B"],
                "dense_scenario": ["A"],
            },
        }


def _profile() -> dict:
    return {
        "purchase_frequency": "3-4 prior purchases",
        "average_prior_rating": 5.0,
        "rating_style": "usually positive",
        "preference_tags": ["comfort"],
        "summary": "Prior purchases emphasize comfort.",
    }


def _sample(scenario: str = "buying") -> dict:
    sample = {
        "sample_id": f"sample_{scenario}",
        "scenario_type": scenario,
        "user_profile": _profile(),
        "ground_truth": {"parent_asin": "A"},
        "intent_card": {
            "target_category": "Blue shoe",
            "hard_constraints": ["leather"],
            "soft_preferences": ["comfortable"],
        },
        "behavior": {"scenario_type": scenario},
    }
    if scenario == "intent_override":
        sample["behavior"]["override"] = {
            "turn": 3,
            "old_value": "comfortable",
            "new_value": "leather",
            "message": "Actually, ignore my earlier preference. What I need is: leather.",
        }
    return sample


class BenchmarkTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.catalog_path = self.root / "catalog.jsonl"
        products = [
            {
                "parent_asin": "A",
                "title": "Blue leather shoe",
                "features": ["comfortable"],
                "details": {},
                "description": [],
                "categories": ["Clothing", "Shoes"],
                "store": "Example",
                "average_rating": 4.5,
                "rating_number": 10,
                "price": 50.0,
            },
            {
                "parent_asin": "B",
                "title": "Red fabric shoe",
                "features": [],
                "details": {},
                "description": [],
                "categories": ["Clothing", "Shoes"],
                "store": "Example",
                "average_rating": 4.0,
                "rating_number": 5,
                "price": 40.0,
            },
        ]
        self.catalog_path.write_text(
            "".join(json.dumps(item) + "\n" for item in products),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.directory.cleanup()

    def _run(self, samples: list[dict], agent_factory=StaticAgent) -> dict:
        dataset_path = self.root / "samples.jsonl"
        dataset_path.write_text(
            "".join(json.dumps(item) + "\n" for item in samples),
            encoding="utf-8",
        )
        config = BenchmarkConfig(
            experiment_name="test",
            catalog_path=str(self.catalog_path),
            dataset_path=str(dataset_path),
            output_root=str(self.root / "runs"),
            split="all",
        )
        summary, _ = run_benchmark(config, agent_factory=agent_factory)
        return summary

    def test_response_validation_reports_contract_problems(self) -> None:
        warnings = validate_response({"message": 1, "ask_attribute": "bad", "recommendations": {}})
        self.assertEqual(
            warnings,
            ["message_not_string", "invalid_ask_attribute", "recommendations_not_list"],
        )

    def test_benchmark_matches_official_metrics(self) -> None:
        samples = [_sample("buying")]
        catalog_ids, categories, products = catalog_index(self.catalog_path)
        official = evaluate(
            StaticAgent(str(self.catalog_path)),
            samples,
            catalog_ids,
            categories,
            products,
        )
        benchmark = self._run(samples)
        for name in ("hit_rate_at_10", "mrr", "mttc", "recommended_technical_score"):
            self.assertEqual(benchmark[name], official[name])

    def test_intent_override_does_not_reset_turn_count(self) -> None:
        summary = self._run([_sample("intent_override")])
        self.assertEqual(summary["hit_rate_at_10"], 1.0)
        self.assertEqual(summary["mrr"], 1.0)
        self.assertEqual(summary["mttc"], 3.0)

    def test_candidate_recall_uses_optional_agent_trace(self) -> None:
        summary = self._run([_sample("buying")], agent_factory=TracedAgent)
        for k in (50, 100, 200):
            self.assertEqual(summary["candidate_metrics"][f"recall_at_{k}"], {
                "measured_sessions": 1,
                "value": 1.0,
            })
        self.assertEqual(
            summary["route_candidate_metrics"]["current_message"]["recall_at_200"],
            1.0,
        )
        self.assertEqual(
            summary["route_candidate_metrics"]["category"]["recall_at_200"],
            1.0,
        )

    def test_dense_sub_routes_are_not_counted_as_lexical(self) -> None:
        summary = self._run([_sample("buying")], agent_factory=DenseViewTracedAgent)

        self.assertEqual(summary["route_union_metrics"], {
            "measured_sessions": 1,
            "lexical_recall_at_200": 0.0,
            "combined_recall_at_200": 1.0,
            "dense_only_addition_rate": 1.0,
        })

    def test_agent_variant_is_written_to_benchmark_artifacts(self) -> None:
        dataset_path = self.root / "variant_samples.jsonl"
        dataset_path.write_text(json.dumps(_sample("buying")) + "\n", encoding="utf-8")
        config = BenchmarkConfig(
            experiment_name="variant",
            catalog_path=str(self.catalog_path),
            dataset_path=str(dataset_path),
            output_root=str(self.root / "variant_runs"),
            split="all",
            agent_variant="vague_3",
            retrieval_variant="multi_route_rrf",
            dense_variant="dense_only",
            reranker_variant="minilm_l4_blended",
            reranker_depth=40,
            reranker_batch_size=16,
            reranker_semantic_weight=0.25,
            orchestration_variant="adaptive_recovery",
        )
        _, run_directory = run_benchmark(config, agent_factory=StaticAgent)
        manifest = json.loads((run_directory / "manifest.json").read_text(encoding="utf-8"))
        saved_config = json.loads((run_directory / "config.json").read_text(encoding="utf-8"))

        self.assertEqual(manifest["agent_variant"], "vague_3")
        self.assertEqual(saved_config["agent_variant"], "vague_3")
        self.assertEqual(manifest["retrieval_variant"], "multi_route_rrf")
        self.assertEqual(saved_config["retrieval_variant"], "multi_route_rrf")
        self.assertEqual(manifest["dense_variant"], "dense_only")
        self.assertEqual(saved_config["dense_variant"], "dense_only")
        self.assertEqual(manifest["reranker_variant"], "minilm_l4_blended")
        self.assertEqual(saved_config["reranker_depth"], 40)
        self.assertEqual(saved_config["reranker_batch_size"], 16)
        self.assertEqual(saved_config["reranker_semantic_weight"], 0.25)
        self.assertEqual(manifest["orchestration_variant"], "adaptive_recovery")
        self.assertEqual(saved_config["orchestration_variant"], "adaptive_recovery")

    def test_orchestration_diagnostics_are_reported(self) -> None:
        summary = self._run([_sample("buying")], agent_factory=TracedAgent)

        diagnostics = summary["orchestration_diagnostics"]
        self.assertEqual(diagnostics["measured_turns"], 1)
        self.assertEqual(diagnostics["executed_mode_counts"], {"precision": 1})
        self.assertEqual(diagnostics["mean_executed_rerank_depth"], 60.0)

    def test_performance_and_artifact_measurements_are_reported(self) -> None:
        summary = self._run([_sample("buying")])

        performance = summary["performance"]
        self.assertGreaterEqual(performance["wall_runtime_ms"], 0.0)
        self.assertGreaterEqual(performance["startup_ms"], 0.0)
        self.assertGreater(
            performance["artifact_sizes"]["bytes"]["catalog"],
            0,
        )

    def test_split_is_deterministic_and_disjoint(self) -> None:
        samples = [
            {"sample_id": f"{scenario}_{index}", "scenario_type": scenario}
            for scenario in ("buying", "browsing", "intent_override", "boundary")
            for index in range(10)
        ]
        development = select_samples(
            samples,
            BenchmarkConfig(experiment_name="x", split="development", seed=7),
        )
        lockbox = select_samples(
            samples,
            BenchmarkConfig(experiment_name="x", split="lockbox", seed=7),
        )
        development_ids = {item["sample_id"] for item in development}
        lockbox_ids = {item["sample_id"] for item in lockbox}
        self.assertEqual(len(development_ids), 32)
        self.assertEqual(len(lockbox_ids), 8)
        self.assertFalse(development_ids & lockbox_ids)
        self.assertEqual(development_ids | lockbox_ids, {item["sample_id"] for item in samples})

    def test_sample_limit_is_deterministic(self) -> None:
        samples = [
            {"sample_id": f"sample_{index}", "scenario_type": "buying"}
            for index in range(20)
        ]
        config = BenchmarkConfig(
            experiment_name="pilot",
            split="all",
            seed=7,
            sample_limit=5,
        )

        first = select_samples(samples, config)
        second = select_samples(list(reversed(samples)), config)

        self.assertEqual(first, second)
        self.assertEqual(len(first), 5)


if __name__ == "__main__":
    unittest.main()
