from __future__ import annotations

import time
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Callable, Mapping

from starter.dense import DenseResult, DenseRetriever
from starter.memory import MemoryUpdater
from starter.reranking import RerankerConfig, RerankResult, SemanticReranker
from starter.retrieval import LexicalRetriever, RetrievalConfig, RetrievalResult
from starter.state import SessionState
from starter.understanding import TurnUnderstanding, UnderstandingEngine


@dataclass
class SkillContext:
    state: SessionState
    user_message: str
    turn: int
    artifacts: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class SkillResult:
    skill_name: str
    output: object
    trace: Mapping[str, object]


SkillFunction = Callable[[SkillContext], SkillResult]


class SkillRegistry:
    """Small in-process directory of named Python capabilities."""

    def __init__(self) -> None:
        self._skills: dict[str, SkillFunction] = {}

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self._skills)

    def register(self, name: str, function: SkillFunction) -> None:
        normalized = name.strip()
        if not normalized:
            raise ValueError("skill name must not be empty")
        if normalized in self._skills:
            raise ValueError(f"skill is already registered: {normalized}")
        if not callable(function):
            raise TypeError("skill must be callable")
        self._skills[normalized] = function

    def run(self, name: str, context: SkillContext) -> SkillResult:
        try:
            function = self._skills[name]
        except KeyError as error:
            raise KeyError(f"unknown skill: {name}") from error

        started = time.perf_counter_ns()
        result = function(context)
        duration_ms = (time.perf_counter_ns() - started) / 1_000_000
        if not isinstance(result, SkillResult):
            raise TypeError(f"skill {name} did not return SkillResult")
        if result.skill_name != name:
            raise ValueError(
                f"skill result name {result.skill_name!r} does not match {name!r}"
            )
        trace = dict(result.trace)
        trace["duration_ms"] = round(duration_ms, 6)
        return SkillResult(name, result.output, MappingProxyType(trace))


def build_skill_registry(
    understanding_engine: UnderstandingEngine,
    memory_updater: MemoryUpdater,
    lexical_retriever: LexicalRetriever | None = None,
    dense_retriever: DenseRetriever | None = None,
    semantic_reranker: SemanticReranker | None = None,
) -> SkillRegistry:
    registry = SkillRegistry()

    def understand_turn(context: SkillContext) -> SkillResult:
        understanding = understanding_engine.understand(
            context.user_message,
            context.state.retrieval_view(),
        )
        parsed = understanding.parsed_turn
        return SkillResult(
            skill_name="understand_turn",
            output=understanding,
            trace={
                "route": understanding.intent.route,
                "confidence": understanding.intent.confidence,
                "reasons": understanding.intent.reasons,
                "events": tuple(event.event_type for event in parsed.events),
                "slots": tuple(update.slot_name for update in parsed.slot_updates),
            },
        )

    def update_memory(context: SkillContext) -> SkillResult:
        understanding = context.artifacts.get("understanding")
        if not isinstance(understanding, TurnUnderstanding):
            raise ValueError("update_memory requires a TurnUnderstanding artifact")
        actions = memory_updater.apply(context.state, understanding)
        view = context.state.retrieval_view()
        return SkillResult(
            skill_name="update_memory",
            output=view,
            trace={
                "actions": actions,
                "search_revision": view.search_revision,
                "context_version": view.context_version,
                "active_slot_names": tuple(view.active_slots),
            },
        )

    registry.register("understand_turn", understand_turn)
    registry.register("update_memory", update_memory)

    if lexical_retriever is not None:
        def retrieve_lexical(context: SkillContext) -> SkillResult:
            route = context.artifacts.get("route", "browsing")
            config = context.artifacts.get("retrieval_config")
            if config is not None and not isinstance(config, RetrievalConfig):
                raise TypeError("retrieval_config artifact must be RetrievalConfig")
            route_weights = context.artifacts.get("lexical_route_weights")
            if route_weights is not None and not isinstance(route_weights, Mapping):
                raise TypeError("lexical_route_weights artifact must be a mapping")
            enabled_routes = context.artifacts.get("lexical_enabled_routes")
            if enabled_routes is not None and not isinstance(enabled_routes, tuple):
                raise TypeError("lexical_enabled_routes artifact must be a tuple")
            result = lexical_retriever.retrieve(
                context.user_message,
                context.state.retrieval_view(),
                str(route),
                config,
                route_weights=route_weights,
                enabled_routes=enabled_routes,
            )
            if not isinstance(result, RetrievalResult):
                raise TypeError("lexical retriever returned an unexpected output type")
            return SkillResult(
                skill_name="retrieve_lexical",
                output=result,
                trace={
                    "config_name": result.config_name,
                    "route_names": tuple(item.name for item in result.routes),
                    "candidate_count": len(result.candidates),
                    "warnings": result.warnings,
                },
            )

        registry.register("retrieve_lexical", retrieve_lexical)

    if dense_retriever is not None:
        def retrieve_dense(context: SkillContext) -> SkillResult:
            result = dense_retriever.retrieve(
                context.user_message,
                context.state.retrieval_view(),
                str(context.artifacts.get("route", "browsing")),
            )
            if not isinstance(result, DenseResult):
                raise TypeError("dense retriever returned an unexpected output type")
            return SkillResult(
                skill_name="retrieve_dense",
                output=result,
                trace={
                    "model_id": result.model_id,
                    "model_revision": result.model_revision,
                    "device": result.device,
                    "query_version": result.query.version,
                    "encode_latency_ms": result.encode_latency_ms,
                    "candidate_count": len(result.candidate_ids),
                    "query_names": tuple(route.name for route in result.routes),
                    "cache_status": result.cache_status,
                },
            )

        registry.register("retrieve_dense", retrieve_dense)

    if semantic_reranker is not None:
        def rerank_candidates(context: SkillContext) -> SkillResult:
            retrieval_result = context.artifacts.get("retrieval_result")
            if not isinstance(retrieval_result, RetrievalResult):
                raise ValueError("rerank_candidates requires a RetrievalResult artifact")
            config = context.artifacts.get("reranker_config")
            if config is not None and not isinstance(config, RerankerConfig):
                raise TypeError("reranker_config artifact must be RerankerConfig")
            result = semantic_reranker.rerank(
                context.user_message,
                context.state.retrieval_view(),
                retrieval_result,
                config,
                str(context.artifacts.get("reranker_route", "buying")),
            )
            if not isinstance(result, RerankResult):
                raise TypeError("semantic reranker returned an unexpected output type")
            return SkillResult(
                skill_name="rerank_candidates",
                output=result,
                trace={
                    "model_id": result.model_id,
                    "model_revision": result.model_revision,
                    "query_version": result.query.version,
                    "context_mode": result.context_mode,
                    "depth": result.depth,
                    "batch_size": result.batch_size,
                    "inference_latency_ms": result.inference_latency_ms,
                    "candidate_count": len(result.candidates),
                },
            )

        registry.register("rerank_candidates", rerank_candidates)
    return registry
