from __future__ import annotations

import unittest

from starter.policy import (
    POLICY_NAMES,
    QuestionPlanner,
    RecommendationConfidenceEstimator,
    RecommendationPolicy,
    RetrievalSignals,
    policy_config,
)
from starter.state import SessionState


def _state(message: str = "I am still exploring.") -> SessionState:
    state = SessionState("session", {})
    state.record_turn(1, message)
    return state


def _signals(
    count: int = 200,
    *,
    separation: float = 0.0,
    override: bool = False,
) -> RetrievalSignals:
    return RetrievalSignals(
        candidate_count=count,
        internal_limit=200,
        score_separation=separation,
        saturated=count >= 200,
        recent_override=override,
    )


class RetrievalSignalsTest(unittest.TestCase):
    def test_score_separation_is_derived_from_bm25_order(self) -> None:
        signals = RetrievalSignals.from_scores((-10.0, -8.0, -7.0), 200)

        self.assertEqual(signals.candidate_count, 3)
        self.assertEqual(signals.score_separation, 0.2)
        self.assertFalse(signals.saturated)


class QuestionPlannerTest(unittest.TestCase):
    def test_planner_skips_resolved_no_preference_and_asked_attributes(self) -> None:
        state = _state()
        state.add_slot_value("category", "women shoes", turn=1, source_text="shoes")
        state.mark_no_preference(
            "material", turn=1, source_text="no preference", clear_existing=False
        )
        first = QuestionPlanner().plan(state.retrieval_view(), "browsing")
        self.assertEqual(first.ask_attribute, "size")

        state.record_clarification(turn=1, attribute="size")
        second = QuestionPlanner().plan(state.retrieval_view(), "browsing")
        self.assertEqual(second.ask_attribute, "budget")

    def test_question_history_is_scoped_to_search_revision(self) -> None:
        state = _state()
        state.record_clarification(turn=1, attribute="category")
        self.assertIn("category", state.retrieval_view().asked_attributes)

        state.start_new_search_revision(turn=1, reason="intent_override")
        self.assertEqual(state.retrieval_view().asked_attributes, ())
        self.assertEqual(
            QuestionPlanner().plan(state.retrieval_view(), "browsing").ask_attribute,
            "category",
        )


class RecommendationPolicyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.candidates = tuple(f"P{index}" for index in range(20))

    def _decide(
        self,
        name: str,
        state: SessionState,
        signals: RetrievalSignals,
        *,
        route: str = "browsing",
        intent_confidence: float = 0.8,
        top_k: int = 10,
    ):
        return RecommendationPolicy(policy_config(name)).decide(
            state.retrieval_view(),
            route,
            intent_confidence,
            signals,
            self.candidates,
            top_k,
        )

    def test_all_named_variants_have_expected_vague_limits(self) -> None:
        expected = {
            "always_10": 10,
            "vague_3": 3,
            "vague_0": 0,
            "dynamic_safe": 0,
        }
        for name in POLICY_NAMES:
            with self.subTest(name=name):
                decision = self._decide(name, _state(), _signals())
                self.assertEqual(decision.recommendation.limit, expected[name])
                self.assertEqual(decision.clarification.ask_attribute, "category")

    def test_specific_buying_query_returns_full_top_k(self) -> None:
        state = _state("I need leather running shoes in size 8.")
        state.add_slot_value(
            "category", "clothing women shoes running", turn=1, source_text="running shoes",
            strength="hard",
        )
        state.add_slot_value(
            "material", "leather", turn=1, source_text="leather", strength="hard"
        )
        state.add_slot_value("size", "8", turn=1, source_text="size 8", strength="hard")

        decision = self._decide(
            "dynamic_safe",
            state,
            _signals(40, separation=0.4),
            route="buying",
            intent_confidence=0.95,
        )

        self.assertEqual(decision.confidence.level, "high")
        self.assertEqual(decision.recommendation.limit, 10)

    def test_late_turn_and_override_favor_coverage(self) -> None:
        late = _state()
        for turn in range(2, 8):
            late.record_turn(turn, "still looking")
        late.record_turn(8, "show me more")
        late_decision = self._decide("dynamic_safe", late, _signals())
        override_decision = self._decide(
            "dynamic_safe", _state(), _signals(20, override=True)
        )

        self.assertEqual(late_decision.recommendation.limit, 10)
        self.assertEqual(override_decision.recommendation.limit, 10)

    def test_empty_pool_and_top_k_cap_are_respected(self) -> None:
        empty = self._decide("always_10", _state(), _signals(0))
        capped = self._decide("always_10", _state(), _signals(20), top_k=4)

        self.assertEqual(empty.recommendation.selected_ids, ())
        self.assertEqual(empty.recommendation.limit, 0)
        self.assertEqual(capped.recommendation.limit, 4)

    def test_unshown_candidates_are_stably_preferred(self) -> None:
        state = _state()
        state.record_shown_products(turn=1, ranked_ids=("P0", "P2"))
        decision = self._decide("always_10", state, _signals(20), top_k=4)

        self.assertEqual(decision.recommendation.selected_ids, ("P1", "P3", "P4", "P5"))

    def test_recommendation_confidence_is_separate_and_inspectable(self) -> None:
        state = _state()
        confidence = RecommendationConfidenceEstimator().estimate(
            state.retrieval_view(), "browsing", 0.9, _signals()
        )

        self.assertIn("intent", confidence.components)
        self.assertNotEqual(confidence.score, confidence.components["intent"])
        self.assertTrue(confidence.over_general)


if __name__ == "__main__":
    unittest.main()
