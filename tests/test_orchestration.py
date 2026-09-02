from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from starter.agent import Agent
from starter.orchestration import (
    AdaptivePlanner,
    OrchestrationSignals,
    PlannerConfig,
)
from starter.retrieval import CandidateEvidence, RetrievalResult, RouteResult
from starter.state import SessionState


def _state(message: str = "I need black boots", turn: int = 1) -> SessionState:
    state = SessionState("session", {})
    for number in range(1, turn + 1):
        state.record_turn(number, message if number == turn else "still looking")
    return state


def _result(count: int = 200, margin: float = 0.01) -> RetrievalResult:
    first = 1.0
    second = first * (1.0 - margin)
    candidates = tuple(
        CandidateEvidence(
            parent_asin=f"P{index}",
            fused_score=first if index == 0 else second / index,
            route_ranks={"current_message": index + 1},
            route_contributions={"current_message": 1.0 / (index + 1)},
            matched_constraints=("category",) if index < 10 else (),
        )
        for index in range(count)
    )
    route = RouteResult(
        "current_message",
        tuple(item.parent_asin for item in candidates),
        tuple(item.fused_score for item in candidates),
    )
    return RetrievalResult(candidates, (route,), (), "multi_route_structured")


class AdaptivePlannerTest(unittest.TestCase):
    def test_static_shadow_proposes_adaptation_but_executes_control(self) -> None:
        state = _state()
        state.add_slot_value(
            "category", "boots", turn=1, source_text="boots", strength="hard"
        )
        planner = AdaptivePlanner(PlannerConfig(name="static_shadow"))
        signals = OrchestrationSignals.from_state(
            state.retrieval_view(), "buying"
        )

        initial = planner.build_initial_plan(signals)
        decision = planner.decide(initial, initial)

        self.assertEqual(initial.mode, "precision")
        self.assertEqual(decision.executed_plan.mode, "static")
        self.assertTrue(decision.shadow)

    def test_vague_saturated_browsing_uses_overload_cutoff(self) -> None:
        planner = AdaptivePlanner(PlannerConfig(name="adaptive_cutoff"))
        signals = OrchestrationSignals.from_state(
            _state("I'm still exploring").retrieval_view(), "browsing"
        )
        initial = planner.build_initial_plan(signals)

        refined = planner.refine_plan(initial, signals.with_retrieval(_result()))
        decision = planner.decide(initial, refined)

        self.assertEqual(decision.executed_plan.mode, "overload_cutoff")
        self.assertFalse(decision.executed_plan.reranker_enabled)
        self.assertEqual(
            decision.executed_plan.recommendation_policy, "always_10"
        )

    def test_clear_browsing_pool_does_not_trigger_cutoff(self) -> None:
        planner = AdaptivePlanner(PlannerConfig(name="adaptive_cutoff"))
        signals = OrchestrationSignals.from_state(
            _state("Show me boots").retrieval_view(), "browsing"
        )
        initial = planner.build_initial_plan(signals)

        refined = planner.refine_plan(
            initial, signals.with_retrieval(_result(count=50, margin=0.5))
        )
        decision = planner.decide(initial, refined)

        self.assertEqual(refined.mode, "exploration")
        self.assertEqual(decision.executed_plan.mode, "static")
        self.assertTrue(decision.executed_plan.reranker_enabled)

    def test_rerank_variant_does_not_inherit_cutoff(self) -> None:
        planner = AdaptivePlanner(PlannerConfig(name="adaptive_rerank"))
        signals = OrchestrationSignals.from_state(
            _state("I'm still exploring").retrieval_view(), "browsing"
        )
        initial = planner.build_initial_plan(signals)
        refined = planner.refine_plan(initial, signals.with_retrieval(_result()))

        decision = planner.decide(initial, refined)

        self.assertEqual(refined.mode, "overload_cutoff")
        self.assertTrue(decision.executed_plan.reranker_enabled)

    def test_override_boundary_and_late_turn_have_distinct_plans(self) -> None:
        planner = AdaptivePlanner(PlannerConfig(name="adaptive_full"))

        override = planner.build_initial_plan(
            OrchestrationSignals.from_state(
                _state("Actually, blue").retrieval_view(),
                "buying",
                ("intent_override",),
            )
        )
        boundary = planner.build_initial_plan(
            OrchestrationSignals.from_state(
                _state("I don't have a preference for color").retrieval_view(),
                "browsing",
                ("no_preference",),
            )
        )
        late = planner.build_initial_plan(
            OrchestrationSignals.from_state(
                _state("still looking", turn=8).retrieval_view(), "browsing"
            )
        )

        self.assertEqual(override.mode, "override_recovery")
        self.assertEqual(override.rerank_depth, 100)
        self.assertEqual(boundary.mode, "boundary_broad")
        self.assertTrue(boundary.lexical_route_weights)
        self.assertEqual(late.mode, "late_coverage")
        self.assertEqual(late.rerank_depth, 100)

    def test_plans_are_deterministic_and_config_is_validated(self) -> None:
        planner = AdaptivePlanner(PlannerConfig(name="adaptive_full"))
        signals = OrchestrationSignals.from_state(
            _state("show me ideas").retrieval_view(), "browsing"
        )

        self.assertEqual(
            planner.build_initial_plan(signals), planner.build_initial_plan(signals)
        )
        with self.assertRaises(ValueError):
            PlannerConfig(name="unknown")
        with self.assertRaises(ValueError):
            PlannerConfig(rerank_depth=-1)


class AgentOrchestrationIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.catalog_path = Path(self.directory.name) / "catalog.jsonl"
        products = (
            {
                "parent_asin": "A",
                "title": "Women's Black Leather Boots",
                "categories": ["Clothing", "Women", "Shoes", "Boots"],
                "features": ["Comfortable"],
                "details": {},
                "description": [],
                "store": "Example",
            },
            {
                "parent_asin": "B",
                "title": "Women's Blue Fabric Boots",
                "categories": ["Clothing", "Women", "Shoes", "Boots"],
                "features": ["Warm"],
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

    def test_shadow_mode_has_exact_static_output_parity(self) -> None:
        static = Agent(
            self.catalog_path,
            reranker_name="rerank_off",
            orchestration_name="static",
        )
        shadow = Agent(
            self.catalog_path,
            reranker_name="rerank_off",
            orchestration_name="static_shadow",
        )
        for agent in (static, shadow):
            agent.reset("same", {"preference_tags": []})

        static_response = static.respond("same", "I need black boots", 1, 10)
        shadow_response = shadow.respond("same", "I need black boots", 1, 10)

        self.assertEqual(shadow_response, static_response)
        trace = shadow.get_last_trace("same")
        self.assertTrue(trace["orchestration"]["shadow"])
        self.assertEqual(
            trace["orchestration"]["executed_plan"]["mode"], "static"
        )

    def test_planner_failure_uses_static_fallback(self) -> None:
        agent = Agent(
            self.catalog_path,
            reranker_name="rerank_off",
            orchestration_name="adaptive_full",
        )
        agent.reset("fallback", {"preference_tags": []})

        with patch.object(
            agent.planner, "build_initial_plan", side_effect=RuntimeError("failed")
        ):
            response = agent.respond("fallback", "I need black boots", 1, 10)

        trace = agent.get_last_trace("fallback")
        self.assertTrue(response["recommendations"])
        self.assertTrue(trace["fallback_used"])
        self.assertTrue(
            any(item.startswith("planner_fallback:RuntimeError") for item in trace["warnings"])
        )
        self.assertEqual(
            trace["orchestration"]["executed_plan"]["mode"], "static"
        )


if __name__ == "__main__":
    unittest.main()
