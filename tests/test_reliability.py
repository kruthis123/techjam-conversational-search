from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from benchmarking.runner import validate_response
from starter.agent import Agent
from starter.reliability import ResponseGuard


class ResponseGuardTest(unittest.TestCase):
    def test_guard_removes_invalid_duplicate_and_excess_recommendations(self) -> None:
        guard = ResponseGuard(("A", "B"))

        result = guard.build(
            message=123,
            ask_attribute="invalid",
            recommendation_ids=("A", "A", "missing", "B"),
            top_k=1,
        )

        self.assertEqual(result.response, {
            "message": "",
            "ask_attribute": None,
            "recommendations": [{"parent_asin": "A"}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0},
        })
        self.assertIn("response_guard:message", result.warnings)
        self.assertIn("response_guard:ask_attribute", result.warnings)
        self.assertEqual(validate_response(result.response), [])


class AgentReliabilityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.catalog_path = Path(self.directory.name) / "catalog.jsonl"
        products = (
            {
                "parent_asin": "A",
                "title": "Black leather slippers",
                "categories": ["Clothing", "Women", "Shoes", "Slippers"],
                "features": ["Comfortable"],
                "details": {},
                "description": [],
                "store": "Example",
                "average_rating": 4.2,
                "rating_number": 10,
                "price": 40.0,
            },
            {
                "parent_asin": "B",
                "title": "Blue fabric slippers",
                "categories": ["Clothing", "Women", "Shoes", "Slippers"],
                "features": ["Indoor"],
                "details": {},
                "description": [],
                "store": "Example",
                "average_rating": 4.8,
                "rating_number": 100,
                "price": 30.0,
            },
            {
                "parent_asin": "C",
                "title": "Winter boots",
                "categories": ["Clothing", "Women", "Shoes", "Boots"],
                "features": ["Warm"],
                "details": {},
                "description": [],
                "store": "Example",
                "average_rating": 4.9,
                "rating_number": 200,
                "price": 80.0,
            },
        )
        self.catalog_path.write_text(
            "".join(json.dumps(product) + "\n" for product in products),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.directory.cleanup()

    def _agent(self) -> Agent:
        agent = Agent(self.catalog_path, reranker_name="rerank_off")
        agent.reset("session", {"preference_tags": []})
        return agent

    def test_catalog_popularity_handles_lexical_and_single_bm25_failure(self) -> None:
        agent = self._agent()
        original_run = agent.skill_registry.run

        def fail_lexical(name, context):
            if name == "retrieve_lexical":
                raise RuntimeError("primary failed")
            return original_run(name, context)

        with (
            patch.object(agent.skill_registry, "run", side_effect=fail_lexical),
            patch.object(agent.retriever, "fallback", side_effect=RuntimeError("failed")),
        ):
            response = agent.respond("session", "I need slippers", 1, 10)

        trace = agent.get_last_trace("session")
        self.assertEqual(trace["retrieval_name"], "catalog_popularity_fallback")
        self.assertEqual(response["recommendations"][0]["parent_asin"], "B")
        self.assertEqual(validate_response(response), [])

    def test_total_retrieval_failure_returns_a_valid_empty_response(self) -> None:
        agent = self._agent()
        original_run = agent.skill_registry.run

        def fail_lexical(name, context):
            if name == "retrieve_lexical":
                raise RuntimeError("primary failed")
            return original_run(name, context)

        with (
            patch.object(agent.skill_registry, "run", side_effect=fail_lexical),
            patch.object(agent.retriever, "fallback", side_effect=RuntimeError("failed")),
            patch.object(
                agent.retriever,
                "catalog_fallback",
                side_effect=RuntimeError("failed"),
            ),
        ):
            response = agent.respond("session", "I need slippers", 1, 10)

        self.assertEqual(response["recommendations"], [])
        self.assertEqual(validate_response(response), [])
        self.assertTrue(agent.get_last_trace("session")["fallback_used"])

    def test_understanding_failure_preserves_the_response_contract(self) -> None:
        agent = self._agent()
        original_run = agent.skill_registry.run

        def fail_understanding(name, context):
            if name == "understand_turn":
                raise RuntimeError("failed")
            return original_run(name, context)

        with patch.object(agent.skill_registry, "run", side_effect=fail_understanding):
            response = agent.respond("session", "I need slippers", 1, 10)

        self.assertEqual(validate_response(response), [])
        self.assertIn(
            "understanding_fallback:RuntimeError",
            agent.get_last_trace("session")["warnings"],
        )

    def test_memory_failure_preserves_the_response_contract(self) -> None:
        agent = self._agent()
        original_run = agent.skill_registry.run

        def fail_memory(name, context):
            if name == "update_memory":
                raise RuntimeError("failed")
            return original_run(name, context)

        with patch.object(agent.skill_registry, "run", side_effect=fail_memory):
            response = agent.respond("session", "I need slippers", 1, 10)

        self.assertEqual(validate_response(response), [])
        self.assertIn(
            "memory_fallback:RuntimeError",
            agent.get_last_trace("session")["warnings"],
        )

    def test_dense_runtime_failure_preserves_lexical_results(self) -> None:
        agent = self._agent()
        agent.dense_retriever = object()
        agent.planner.config = replace(agent.planner.config, dense_name="test-dense")

        def fail_dense(context):
            raise RuntimeError("failed")

        agent.skill_registry.register("retrieve_dense", fail_dense)
        response = agent.respond("session", "I need slippers", 1, 10)

        trace = agent.get_last_trace("session")
        self.assertEqual(validate_response(response), [])
        self.assertIn("dense_runtime_fallback:RuntimeError:failed", trace["warnings"])
        self.assertEqual(trace["retrieval_name"], "multi_route_structured")

    def test_reranker_runtime_failure_preserves_lexical_order(self) -> None:
        agent = self._agent()
        agent.semantic_reranker = object()
        agent.planner.config = replace(
            agent.planner.config,
            reranker_name="test-reranker",
        )

        def fail_reranker(context):
            raise RuntimeError("failed")

        agent.skill_registry.register("rerank_candidates", fail_reranker)
        response = agent.respond("session", "I need slippers", 1, 10)

        trace = agent.get_last_trace("session")
        self.assertEqual(validate_response(response), [])
        self.assertIn("reranker_runtime_fallback:RuntimeError:failed", trace["warnings"])
        self.assertEqual(trace["candidate_ids"], trace["pre_rerank_candidate_ids"])


if __name__ == "__main__":
    unittest.main()
