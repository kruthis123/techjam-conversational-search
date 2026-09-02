from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping, Sequence

from starter.retrieval import RetrievalResult
from starter.state import StateView


ORCHESTRATION_NAMES = (
    "static",
    "static_shadow",
    "adaptive_rerank",
    "adaptive_cutoff",
    "adaptive_recovery",
    "adaptive_full",
)
PLAN_VERSION = "1.0"


@dataclass(frozen=True)
class PlannerConfig:
    name: str = "static"
    retrieval_name: str = "multi_route_structured"
    lexical_depth: int = 400
    fusion_depth: int = 200
    dense_name: str = "dense_off"
    reranker_name: str = "minilm_l4_blended"
    rerank_depth: int = 60
    semantic_rank_weight: float = 0.25
    recommendation_policy: str = "always_10"
    late_turn: int = 8
    recovery_rerank_depth: int = 100
    exploration_rerank_depth: int = 40
    overload_slot_limit: int = 2
    overload_margin: float = 0.08

    def __post_init__(self) -> None:
        normalized = self.name.strip().casefold()
        if normalized not in ORCHESTRATION_NAMES:
            raise ValueError(
                f"orchestration name must be one of {ORCHESTRATION_NAMES}"
            )
        object.__setattr__(self, "name", normalized)
        for field_name in (
            "lexical_depth",
            "fusion_depth",
            "rerank_depth",
            "recovery_rerank_depth",
            "exploration_rerank_depth",
        ):
            if getattr(self, field_name) < 0:
                raise ValueError(f"{field_name} must not be negative")
        if not 1 <= self.late_turn <= 10:
            raise ValueError("late_turn must be between 1 and 10")
        if self.overload_slot_limit < 0:
            raise ValueError("overload_slot_limit must not be negative")
        if not 0.0 <= self.overload_margin <= 1.0:
            raise ValueError("overload_margin must be between 0 and 1")
        if self.semantic_rank_weight < 0:
            raise ValueError("semantic_rank_weight must not be negative")


@dataclass(frozen=True)
class OrchestrationSignals:
    route: str
    turn_number: int
    active_slot_count: int
    hard_constraint_count: int
    is_override: bool
    has_no_preference: bool
    candidate_count: int | None = None
    route_count: int | None = None
    score_margin: float | None = None
    constraint_coverage: float | None = None

    @classmethod
    def from_state(
        cls,
        state: StateView,
        route: str,
        event_types: Sequence[str] = (),
    ) -> OrchestrationSignals:
        hard_count = sum(
            value.strength == "hard"
            for slot in state.active_slots.values()
            for value in slot.values
        )
        event_set = set(event_types)
        return cls(
            route=route,
            turn_number=state.turn,
            active_slot_count=len(state.active_slots),
            hard_constraint_count=hard_count,
            is_override=bool(
                {"intent_override", "full_restart"} & event_set
            ),
            has_no_preference=bool(
                {"no_preference", "no_additional_preference"} & event_set
            ),
        )

    def with_retrieval(self, result: RetrievalResult) -> OrchestrationSignals:
        candidates = result.candidates
        margin = 0.0
        if len(candidates) >= 2:
            first = candidates[0].fused_score
            second = candidates[1].fused_score
            margin = max(0.0, min(1.0, (first - second) / max(abs(first), 1e-9)))

        active_constraints = {
            name
            for candidate in candidates[:10]
            for name in candidate.matched_constraints
        }
        coverage = (
            1.0
            if self.active_slot_count == 0
            else min(1.0, len(active_constraints) / self.active_slot_count)
        )
        return replace(
            self,
            candidate_count=len(candidates),
            route_count=sum(bool(route.candidate_ids) for route in result.routes),
            score_margin=round(margin, 4),
            constraint_coverage=round(coverage, 4),
        )


@dataclass(frozen=True)
class RetrievalPlan:
    version: str
    mode: str
    reasons: tuple[str, ...]
    skill_order: tuple[str, ...]
    retrieval_name: str
    lexical_route_weights: tuple[tuple[str, float], ...]
    lexical_enabled_routes: tuple[str, ...]
    lexical_depth: int
    fusion_depth: int
    dense_enabled: bool
    reranker_enabled: bool
    rerank_depth: int
    semantic_rank_weight: float
    recommendation_policy: str
    clarification_priority: str | None = None

    @property
    def route_weights(self) -> Mapping[str, float] | None:
        return dict(self.lexical_route_weights) or None

    def as_trace(self) -> dict[str, object]:
        return {
            "version": self.version,
            "mode": self.mode,
            "reasons": self.reasons,
            "skill_order": self.skill_order,
            "retrieval_name": self.retrieval_name,
            "lexical_route_weights": dict(self.lexical_route_weights),
            "lexical_enabled_routes": self.lexical_enabled_routes,
            "lexical_depth": self.lexical_depth,
            "fusion_depth": self.fusion_depth,
            "dense_enabled": self.dense_enabled,
            "reranker_enabled": self.reranker_enabled,
            "rerank_depth": self.rerank_depth,
            "semantic_rank_weight": self.semantic_rank_weight,
            "recommendation_policy": self.recommendation_policy,
            "clarification_priority": self.clarification_priority,
        }


@dataclass(frozen=True)
class PlanDecision:
    orchestration_name: str
    initial_plan: RetrievalPlan
    proposed_plan: RetrievalPlan
    executed_plan: RetrievalPlan
    changed_fields: tuple[str, ...]
    shadow: bool
    fallback_reason: str | None = None

    def as_trace(self) -> dict[str, object]:
        return {
            "orchestration_name": self.orchestration_name,
            "shadow": self.shadow,
            "initial_plan": self.initial_plan.as_trace(),
            "proposed_plan": self.proposed_plan.as_trace(),
            "executed_plan": self.executed_plan.as_trace(),
            "changed_fields": self.changed_fields,
            "fallback_reason": self.fallback_reason,
        }


class AdaptivePlanner:
    """Compile active session state into a deterministic per-turn plan."""

    BROWSING_WEIGHTS = (
        ("current_message", 1.2),
        ("category", 1.5),
        ("latest_constraint", 0.9),
        ("complete_state", 1.0),
        ("title_heavy", 0.7),
        ("feature_heavy", 1.5),
        ("structured", 1.0),
    )
    BOUNDARY_WEIGHTS = (
        ("current_message", 1.0),
        ("category", 1.3),
        ("latest_constraint", 0.5),
        ("complete_state", 1.3),
        ("title_heavy", 1.0),
        ("feature_heavy", 1.2),
        ("structured", 1.2),
    )

    def __init__(self, config: PlannerConfig) -> None:
        self.config = config

    def static_plan(self) -> RetrievalPlan:
        dense_enabled = self.config.dense_name != "dense_off"
        reranker_enabled = self.config.reranker_name != "rerank_off"
        return RetrievalPlan(
            version=PLAN_VERSION,
            mode="static",
            reasons=("frozen configured pipeline",),
            skill_order=self._skill_order(dense_enabled, reranker_enabled),
            retrieval_name=self.config.retrieval_name,
            lexical_route_weights=(),
            lexical_enabled_routes=(),
            lexical_depth=self.config.lexical_depth,
            fusion_depth=self.config.fusion_depth,
            dense_enabled=dense_enabled,
            reranker_enabled=reranker_enabled,
            rerank_depth=self.config.rerank_depth,
            semantic_rank_weight=self.config.semantic_rank_weight,
            recommendation_policy=self.config.recommendation_policy,
        )

    def build_initial_plan(self, signals: OrchestrationSignals) -> RetrievalPlan:
        plan = self.static_plan()
        if signals.is_override:
            return replace(
                plan,
                mode="override_recovery",
                reasons=("search revision changed this turn",),
                rerank_depth=max(plan.rerank_depth, self.config.recovery_rerank_depth),
            )
        if signals.turn_number >= self.config.late_turn:
            return replace(
                plan,
                mode="late_coverage",
                reasons=("late-turn coverage pressure",),
                rerank_depth=max(plan.rerank_depth, self.config.recovery_rerank_depth),
            )
        if signals.has_no_preference:
            return replace(
                plan,
                mode="boundary_broad",
                reasons=("user rejected an attribute constraint",),
                lexical_route_weights=self.BOUNDARY_WEIGHTS,
                rerank_depth=max(plan.rerank_depth, 80),
                clarification_priority="unresolved_attribute",
            )
        if signals.route == "buying" and signals.hard_constraint_count > 0:
            return replace(
                plan,
                mode="precision",
                reasons=("buying route with hard constraints",),
            )
        return replace(
            plan,
            mode="exploration",
            reasons=("browsing or weakly constrained request",),
            lexical_route_weights=self.BROWSING_WEIGHTS,
            rerank_depth=min(plan.rerank_depth, self.config.exploration_rerank_depth),
            clarification_priority="highest_utility",
        )

    def refine_plan(
        self,
        initial_plan: RetrievalPlan,
        signals: OrchestrationSignals,
    ) -> RetrievalPlan:
        if (
            signals.route == "browsing"
            and signals.active_slot_count <= self.config.overload_slot_limit
            and (signals.candidate_count or 0) >= initial_plan.fusion_depth
            and (signals.score_margin or 0.0) < self.config.overload_margin
        ):
            return replace(
                initial_plan,
                mode="overload_cutoff",
                reasons=initial_plan.reasons
                + ("saturated weakly-separated candidate pool",),
                dense_enabled=False,
                reranker_enabled=False,
                skill_order=self._skill_order(False, False),
                clarification_priority="highest_utility",
            )
        return initial_plan

    def decide(
        self,
        initial_plan: RetrievalPlan,
        proposed_plan: RetrievalPlan,
    ) -> PlanDecision:
        executed = self._select_executed(proposed_plan)
        return PlanDecision(
            orchestration_name=self.config.name,
            initial_plan=initial_plan,
            proposed_plan=proposed_plan,
            executed_plan=executed,
            changed_fields=self._changed_fields(initial_plan, proposed_plan),
            shadow=self.config.name == "static_shadow",
        )

    def fallback_decision(self, reason: str) -> PlanDecision:
        plan = self.static_plan()
        return PlanDecision(self.config.name, plan, plan, plan, (), False, reason)

    def _select_executed(self, proposed: RetrievalPlan) -> RetrievalPlan:
        name = self.config.name
        static = self.static_plan()
        if name in {"static", "static_shadow"}:
            return static
        if name == "adaptive_rerank":
            return replace(
                static,
                mode=proposed.mode,
                reasons=proposed.reasons,
                reranker_enabled=static.reranker_enabled,
                rerank_depth=proposed.rerank_depth,
                skill_order=self._skill_order(
                    static.dense_enabled, static.reranker_enabled
                ),
            )
        if name == "adaptive_cutoff":
            if proposed.mode != "overload_cutoff":
                return static
            return replace(
                static,
                mode=proposed.mode,
                reasons=proposed.reasons,
                dense_enabled=False,
                reranker_enabled=False,
                skill_order=self._skill_order(False, False),
            )
        if name == "adaptive_recovery":
            if proposed.mode not in {
                "override_recovery",
                "boundary_broad",
                "late_coverage",
            }:
                return static
            return proposed
        return proposed

    def _skill_order(
        self, dense_enabled: bool, reranker_enabled: bool
    ) -> tuple[str, ...]:
        names = ["understand_turn", "update_memory", "retrieve_lexical"]
        if dense_enabled:
            names.append("retrieve_dense")
        if reranker_enabled:
            names.append("rerank_candidates")
        return tuple(names)

    def _changed_fields(
        self, before: RetrievalPlan, after: RetrievalPlan
    ) -> tuple[str, ...]:
        fields = (
            "mode",
            "lexical_route_weights",
            "lexical_enabled_routes",
            "lexical_depth",
            "fusion_depth",
            "dense_enabled",
            "reranker_enabled",
            "rerank_depth",
            "semantic_rank_weight",
            "recommendation_policy",
            "clarification_priority",
        )
        return tuple(name for name in fields if getattr(before, name) != getattr(after, name))
