from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from starter.agent import Agent
from starter.memory import MemoryUpdater
from starter.skills import (
    SkillContext,
    SkillRegistry,
    SkillResult,
    build_skill_registry,
)
from starter.state import SessionStore
from starter.understanding import CatalogVocabularyBuilder, UnderstandingEngine


class SkillRegistryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.state = SessionStore().reset("session", {"preference_tags": []})
        self.state.record_turn(1, "hello")
        self.context = SkillContext(self.state, "hello", 1)

    def test_registry_runs_and_times_a_named_python_function(self) -> None:
        registry = SkillRegistry()

        def echo(context: SkillContext) -> SkillResult:
            return SkillResult("echo", context.user_message, {"kind": "deterministic"})

        registry.register("echo", echo)
        result = registry.run("echo", self.context)

        self.assertEqual(registry.names, ("echo",))
        self.assertEqual(result.output, "hello")
        self.assertEqual(result.trace["kind"], "deterministic")
        self.assertIn("duration_ms", result.trace)

    def test_registry_rejects_duplicate_unknown_and_invalid_skills(self) -> None:
        registry = SkillRegistry()
        registry.register("bad", lambda context: "not a SkillResult")
        with self.assertRaises(ValueError):
            registry.register("bad", lambda context: SkillResult("bad", None, {}))
        with self.assertRaises(KeyError):
            registry.run("missing", self.context)
        with self.assertRaises(TypeError):
            registry.run("bad", self.context)

    def test_default_skills_pass_understanding_into_memory(self) -> None:
        builder = CatalogVocabularyBuilder()
        builder.observe(
            {
                "categories": ["Clothing", "Women", "Shoes", "Slippers"],
                "store": "Example",
            }
        )
        registry = build_skill_registry(
            UnderstandingEngine(builder.build()),
            MemoryUpdater(),
        )
        context = SkillContext(self.state, "I need women's leather slippers.", 1)

        understanding = registry.run("understand_turn", context)
        context.artifacts["understanding"] = understanding.output
        memory = registry.run("update_memory", context)

        self.assertEqual(understanding.trace["route"], "buying")
        self.assertIn("category", memory.output.active_constraints)
        self.assertEqual(memory.output.active_constraints["material"], ("leather",))


class AgentUnderstandingIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.catalog_path = Path(self.directory.name) / "catalog.jsonl"
        products = (
            {
                "parent_asin": "A",
                "title": "Clarks Women's Black Leather Slippers",
                "categories": ["Clothing", "Women", "Shoes", "Slippers"],
                "features": ["Comfortable"],
                "details": {"Brand": "Clarks"},
                "description": [],
                "store": "Clarks",
            },
            {
                "parent_asin": "B",
                "title": "Blue Fabric Shoes",
                "categories": ["Clothing", "Women", "Shoes"],
                "features": [],
                "details": {},
                "description": [],
                "store": "Example",
            },
        )
        self.catalog_path.write_text(
            "".join(json.dumps(product) + "\n" for product in products),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_agent_updates_state_and_keeps_official_response_contract(self) -> None:
        agent = Agent(self.catalog_path, reranker_name="rerank_off")
        agent.reset("one", {"preference_tags": ["comfort"]})
        response = agent.respond(
            "one",
            "I need Clarks women's black leather slippers.",
            1,
            10,
        )
        trace = agent.get_last_trace("one")

        self.assertEqual(set(response), {"message", "ask_attribute", "recommendations", "usage"})
        self.assertEqual(trace["inferred_route"], "buying")
        self.assertIn("recommendation_confidence", trace)
        self.assertIn("intent_confidence", trace)
        self.assertEqual(trace["policy_name"], "always_10")
        self.assertFalse(trace["fallback_used"])
        self.assertIn("category", {slot["name"] for slot in trace["active_slots"]})

        agent.reset("two", {"preference_tags": []})
        agent.respond("two", "I'm still exploring.", 1, 10)
        self.assertEqual(agent.get_last_trace("two")["inferred_route"], "browsing")
        self.assertNotEqual(
            agent.session_store.get("one").active_constraints(),
            agent.session_store.get("two").active_constraints(),
        )

    def test_agent_policy_variants_preserve_top_k_contract(self) -> None:
        for policy_name in ("always_10", "vague_3", "vague_0", "dynamic_safe"):
            with self.subTest(policy_name=policy_name):
                agent = Agent(
                    self.catalog_path,
                    policy_name=policy_name,
                    reranker_name="rerank_off",
                )
                agent.reset(policy_name, {"preference_tags": []})
                response = agent.respond(policy_name, "I'm still exploring.", 1, 1)
                self.assertLessEqual(len(response["recommendations"]), 1)
                self.assertIn(response["ask_attribute"], {
                    "category", "material", "color", "size", "style", "brand",
                    "budget", "feature", "use_case", "other", None,
                })

    def test_agent_uses_deterministic_policy_fallback(self) -> None:
        agent = Agent(
            self.catalog_path,
            policy_name="dynamic_safe",
            reranker_name="rerank_off",
        )
        agent.reset("fallback", {"preference_tags": []})

        with patch.object(agent.policy, "decide", side_effect=RuntimeError("failed")):
            response = agent.respond("fallback", "I need leather slippers.", 1, 10)

        trace = agent.get_last_trace("fallback")
        self.assertTrue(trace["fallback_used"])
        self.assertIn("policy_fallback:RuntimeError", trace["warnings"])
        self.assertLessEqual(len(response["recommendations"]), 10)

    def test_agent_exposes_multi_route_retrieval_evidence(self) -> None:
        agent = Agent(
            self.catalog_path,
            retrieval_name="multi_route_structured",
            reranker_name="rerank_off",
        )
        agent.reset("retrieval", {"preference_tags": []})

        agent.respond("retrieval", "I need leather slippers.", 1, 10)
        trace = agent.get_last_trace("retrieval")

        self.assertEqual(trace["retrieval_name"], "multi_route_structured")
        self.assertIn("current_message", trace["route_candidate_ids"])
        self.assertIn("complete_state", trace["compiled_queries"])
        self.assertTrue(trace["candidate_evidence"])

    def test_agent_falls_back_when_retrieval_skill_fails(self) -> None:
        agent = Agent(
            self.catalog_path,
            retrieval_name="multi_route_rrf",
            reranker_name="rerank_off",
        )
        agent.reset("retrieval-fallback", {"preference_tags": []})
        original_run = agent.skill_registry.run

        def run_with_failure(name, context):
            if name == "retrieve_lexical":
                raise RuntimeError("failed")
            return original_run(name, context)

        with patch.object(agent.skill_registry, "run", side_effect=run_with_failure):
            response = agent.respond(
                "retrieval-fallback", "I need leather slippers.", 1, 10
            )

        trace = agent.get_last_trace("retrieval-fallback")
        self.assertEqual(trace["retrieval_name"], "single_bm25")
        self.assertIn("retrieval_fallback:RuntimeError", trace["warnings"])
        self.assertTrue(response["recommendations"])

    def test_agent_falls_back_when_dense_artifacts_are_missing(self) -> None:
        agent = Agent(
            self.catalog_path,
            dense_name="hybrid_dense",
            dense_model_directory=Path(self.directory.name) / "missing-model",
            dense_cache_directory=Path(self.directory.name) / "missing-cache",
            reranker_name="rerank_off",
        )
        agent.reset("dense-fallback", {"preference_tags": []})

        response = agent.respond("dense-fallback", "I need leather slippers.", 1, 10)

        trace = agent.get_last_trace("dense-fallback")
        self.assertEqual(trace["retrieval_name"], "multi_route_structured")
        self.assertEqual(trace["dense_name"], "hybrid_dense")
        self.assertTrue(trace["fallback_used"])
        self.assertTrue(
            any(item.startswith("dense_startup_fallback:") for item in trace["warnings"])
        )
        self.assertTrue(response["recommendations"])

    def test_agent_falls_back_when_reranker_artifacts_are_missing(self) -> None:
        agent = Agent(
            self.catalog_path,
            reranker_name="minilm_l4_blended",
            reranker_model_directory=Path(self.directory.name) / "missing-reranker",
        )
        agent.reset("reranker-fallback", {"preference_tags": []})

        response = agent.respond(
            "reranker-fallback", "I need leather slippers.", 1, 10
        )

        trace = agent.get_last_trace("reranker-fallback")
        self.assertEqual(trace["retrieval_name"], "multi_route_structured")
        self.assertEqual(trace["reranker_name"], "minilm_l4_blended")
        self.assertTrue(trace["fallback_used"])
        self.assertTrue(
            any(
                item.startswith("reranker_startup_fallback:")
                for item in trace["warnings"]
            )
        )
        self.assertTrue(response["recommendations"])


if __name__ == "__main__":
    unittest.main()
