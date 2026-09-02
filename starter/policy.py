from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from starter.state import StateView


POLICY_VERSION = "1.0"
POLICY_NAMES = ("always_10", "vague_3", "vague_0", "dynamic_safe")
PRICE_SLOTS = {"min_price", "max_price", "target_price"}


@dataclass(frozen=True)
class RetrievalSignals:
    candidate_count: int
    internal_limit: int
    top_scores: tuple[float, ...] = ()
    score_separation: float = 0.0
    saturated: bool = False
    recent_override: bool = False

    @classmethod
    def from_scores(
        cls,
        scores: Sequence[float],
        internal_limit: int,
        *,
        recent_override: bool = False,
    ) -> "RetrievalSignals":
        top_scores = tuple(float(score) for score in scores[:3])
        separation = 0.0
        if len(top_scores) >= 2:
            denominator = max(abs(top_scores[0]), 1e-9)
            separation = min(1.0, max(0.0, (top_scores[1] - top_scores[0]) / denominator))
        return cls(
            candidate_count=len(scores),
            internal_limit=internal_limit,
            top_scores=top_scores,
            score_separation=round(separation, 4),
            saturated=len(scores) >= internal_limit,
            recent_override=recent_override,
        )


@dataclass(frozen=True)
class RecommendationConfidence:
    score: float
    level: str
    over_general: bool
    components: Mapping[str, float]
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ClarificationDecision:
    ask_attribute: str | None
    utility: float
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class RecommendationDecision:
    limit: int
    selected_ids: tuple[str, ...]
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class PolicyDecision:
    confidence: RecommendationConfidence
    clarification: ClarificationDecision
    recommendation: RecommendationDecision
    message: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class PolicyConfig:
    name: str
    version: str = POLICY_VERSION
    moderate_threshold: float = 0.45
    high_threshold: float = 0.68
    late_turn: int = 8


def policy_config(name: str) -> PolicyConfig:
    normalized = name.strip().casefold()
    if normalized not in POLICY_NAMES:
        raise ValueError(f"policy name must be one of {POLICY_NAMES}")
    return PolicyConfig(name=normalized)


class RecommendationConfidenceEstimator:
    """Estimate ranking confidence from deterministic, inspectable signals."""

    def estimate(
        self,
        state: StateView,
        route: str,
        intent_confidence: float,
        signals: RetrievalSignals,
    ) -> RecommendationConfidence:
        hard_count = sum(
            value.strength == "hard"
            for slot in state.active_slots.values()
            for value in slot.values
        )
        soft_count = sum(
            value.strength == "soft"
            for slot in state.active_slots.values()
            for value in slot.values
        )
        resolved_count = len(state.active_slots) + len(state.no_preference_attributes)
        category_specificity = self._category_specificity(state)
        constraint_strength = min(1.0, hard_count * 0.25 + soft_count * 0.12)
        pool_quality = 0.0 if signals.candidate_count == 0 else 1.0
        turn_urgency = min(1.0, max(0.0, (state.turn - 1) / 7.0))
        saturation_penalty = 1.0 if signals.saturated and resolved_count <= 2 else 0.0

        score = (
            0.08
            + 0.16 * max(0.0, min(1.0, intent_confidence))
            + 0.22 * constraint_strength
            + 0.17 * category_specificity
            + 0.13 * signals.score_separation
            + 0.08 * pool_quality
            + 0.08 * turn_urgency
            + (0.06 if route == "buying" else -0.06)
            - 0.12 * saturation_penalty
            - (0.08 if signals.recent_override else 0.0)
        )
        score = round(max(0.0, min(1.0, score)), 4)
        over_general = (
            signals.saturated
            and resolved_count <= 2
            and signals.score_separation < 0.08
        )
        level = "high" if score >= 0.68 else "medium" if score >= 0.45 else "low"
        reasons = [f"{hard_count} hard and {soft_count} soft constraints"]
        if over_general:
            reasons.append("saturated weakly-separated candidate pool")
        if signals.recent_override:
            reasons.append("search revision changed this turn")
        if state.turn >= 8:
            reasons.append("late-turn coverage pressure")
        return RecommendationConfidence(
            score=score,
            level=level,
            over_general=over_general,
            components={
                "intent": round(intent_confidence, 4),
                "constraint_strength": round(constraint_strength, 4),
                "category_specificity": round(category_specificity, 4),
                "score_separation": round(signals.score_separation, 4),
                "pool_quality": pool_quality,
                "turn_urgency": round(turn_urgency, 4),
                "saturation_penalty": saturation_penalty,
            },
            reasons=tuple(reasons),
        )

    def _category_specificity(self, state: StateView) -> float:
        values = state.active_constraints.get("category", ())
        if not values:
            return 0.0
        word_count = len(str(values[0]).replace(">", " ").split())
        return min(1.0, word_count / 4.0)


class QuestionPlanner:
    """Choose one useful unresolved attribute for the next simulator reply."""

    PRIORITIES = {
        "shoes": ("material", "size", "budget", "color", "feature", "style"),
        "clothing": ("size", "style", "material", "color", "budget", "feature"),
        "jewelry": ("budget", "material", "style", "feature", "color"),
        "browsing": ("category", "use_case", "style", "budget", "feature"),
        "default": ("feature", "material", "color", "budget", "style", "other"),
    }

    def plan(self, state: StateView, route: str) -> ClarificationDecision:
        group = self._category_group(state)
        priorities = self.PRIORITIES[group or ("browsing" if route == "browsing" else "default")]
        resolved = set(state.active_slots) | set(state.no_preference_attributes)
        if PRICE_SLOTS & set(state.active_slots):
            resolved.add("budget")
        asked = set(state.asked_attributes)

        for index, attribute in enumerate(priorities):
            if attribute not in resolved and attribute not in asked:
                return ClarificationDecision(
                    ask_attribute=attribute,
                    utility=round(max(0.1, 1.0 - index * 0.12), 2),
                    reasons=(f"highest unresolved {group or route} attribute",),
                )
        return ClarificationDecision(
            ask_attribute=None,
            utility=0.0,
            reasons=("all planned attributes are resolved or already asked",),
        )

    def _category_group(self, state: StateView) -> str | None:
        category = " ".join(str(value) for value in state.active_constraints.get("category", ()))
        if any(word in category for word in ("shoe", "boot", "slipper", "sandal", "sneaker")):
            return "shoes"
        if any(word in category for word in ("jewelry", "ring", "necklace", "bracelet", "earring")):
            return "jewelry"
        clothing_words = ("shirt", "dress", "coat", "pant", "clothing", "apparel")
        if any(word in category for word in clothing_words):
            return "clothing"
        return None


class RecommendationPolicy:
    def __init__(self, config: PolicyConfig) -> None:
        self.config = config
        self.confidence_estimator = RecommendationConfidenceEstimator()
        self.question_planner = QuestionPlanner()

    def decide(
        self,
        state: StateView,
        route: str,
        intent_confidence: float,
        signals: RetrievalSignals,
        ranked_candidate_ids: Sequence[str],
        top_k: int,
    ) -> PolicyDecision:
        confidence = self.confidence_estimator.estimate(
            state, route, intent_confidence, signals
        )
        clarification = self.question_planner.plan(state, route)
        requested_limit, limit_reason = self._recommendation_limit(
            state, route, confidence, signals, top_k
        )
        selected = self._select_candidates(
            ranked_candidate_ids,
            state.shown_product_ids,
            min(requested_limit, top_k),
        )
        recommendation = RecommendationDecision(
            limit=len(selected),
            selected_ids=selected,
            reasons=(limit_reason,),
        )
        message = self._message(len(selected), clarification.ask_attribute)
        return PolicyDecision(
            confidence=confidence,
            clarification=clarification,
            recommendation=recommendation,
            message=message,
            reasons=(f"policy={self.config.name}", limit_reason),
        )

    def _recommendation_limit(
        self,
        state: StateView,
        route: str,
        confidence: RecommendationConfidence,
        signals: RetrievalSignals,
        top_k: int,
    ) -> tuple[int, str]:
        cap = max(0, top_k)
        if signals.candidate_count == 0 or cap == 0:
            return 0, "no usable candidates"
        if self.config.name == "always_10":
            return cap, "coverage control returns full top-k"
        if state.turn >= self.config.late_turn:
            return cap, "late turn favors coverage"
        if signals.recent_override:
            return cap, "override recovery rebuilds full recommendations"
        if self.config.name == "vague_3":
            if confidence.over_general and state.turn <= 3:
                return min(3, cap), "vague early query capped at three"
            return cap, "query is outside vague early cutoff"
        if self.config.name == "vague_0":
            if confidence.over_general and state.turn <= 3:
                return 0, "vague early query uses strict retrieval cutoff"
            return cap, "query is outside vague early cutoff"

        if confidence.over_general and route == "browsing" and state.turn <= 2:
            if confidence.score < 0.30:
                return 0, "extremely vague browsing query uses retrieval cutoff"
            return min(3, cap), "vague browsing query returns only three"
        if confidence.score >= self.config.high_threshold and route == "buying":
            return cap, "specific buying query favors coverage"
        if confidence.score >= self.config.moderate_threshold:
            return min(5, cap), "moderate confidence returns five"
        return min(3, cap), "low confidence returns three"

    def _select_candidates(
        self,
        ranked_ids: Sequence[str],
        shown_ids: Sequence[str],
        limit: int,
    ) -> tuple[str, ...]:
        if limit <= 0:
            return ()
        shown = set(shown_ids)
        unique = tuple(dict.fromkeys(str(item) for item in ranked_ids if str(item)))
        unshown = [item for item in unique if item not in shown]
        repeated = [item for item in unique if item in shown]
        return tuple((unshown + repeated)[:limit])

    def _message(self, recommendation_count: int, ask_attribute: str | None) -> str:
        if recommendation_count and ask_attribute:
            return (
                f"I found {recommendation_count} promising options. "
                f"To narrow them down, what is your preferred {ask_attribute.replace('_', ' ')}?"
            )
        if recommendation_count:
            return f"Here are the {recommendation_count} closest matches I found."
        if ask_attribute:
            return (
                "I need one detail before recommending products. "
                f"What is your preferred {ask_attribute.replace('_', ' ')}?"
            )
        return "I could not find a reliable match yet. Please add one product preference."
