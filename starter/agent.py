from __future__ import annotations

import json
import sqlite3
from dataclasses import replace
from pathlib import Path
from typing import cast

from starter.catalog import Product
from starter.catalog_cache import sha256_file
from starter.dense import (
    DenseResult,
    DenseRetriever,
    SentenceTransformerEncoder,
    dense_config,
)
from starter.memory import MemoryUpdater
from starter.orchestration import (
    AdaptivePlanner,
    OrchestrationSignals,
    PlanDecision,
    PlannerConfig,
)
from starter.policy import (
    PolicyDecision,
    RecommendationPolicy,
    RetrievalSignals,
    policy_config,
)
from starter.reranking import (
    CrossEncoderScorer,
    RerankResult,
    SemanticReranker,
    load_reranker_manifest,
    reranker_config,
)
from starter.reliability import ResponseGuard
from starter.retrieval import (
    LexicalRetriever,
    RetrievalResult,
    fuse_lexical_and_dense,
    fuse_lexical_and_dense_rescue,
    retrieval_config,
)
from starter.skills import SkillContext, build_skill_registry
from starter.state import SessionStore, StateView
from starter.understanding import (
    CatalogVocabulary,
    CatalogVocabularyBuilder,
    TurnUnderstanding,
    UnderstandingEngine,
)


def _text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return " ".join(f"{key} {item}" for key, item in value.items())
    if isinstance(value, list):
        return " ".join(str(item) for item in value)
    return str(value)

class Agent:
    """Stateful understanding with the original BM25 retrieval kept as a baseline."""

    INTERNAL_CANDIDATE_LIMIT = 200

    def __init__(
        self,
        catalog_path: str | Path = "data/catalog.jsonl",
        policy_name: str = "always_10",
        retrieval_name: str = "multi_route_structured",
        dense_name: str = "dense_off",
        dense_model_directory: str | Path | None = None,
        dense_cache_directory: str | Path | None = None,
        dense_device: str = "cpu",
        reranker_name: str = "minilm_l4_blended",
        reranker_model_directory: str | Path | None = None,
        reranker_depth: int | None = None,
        reranker_batch_size: int | None = None,
        reranker_semantic_weight: float | None = None,
        reranker_device: str = "cpu",
        orchestration_name: str = "adaptive_cutoff",
    ) -> None:
        self.catalog_path = Path(catalog_path)
        self.policy = RecommendationPolicy(policy_config(policy_name))
        self.connection = sqlite3.connect(":memory:")
        self._normalized_products: list[Product] = []
        self.vocabulary = self._build_index()
        self.response_guard = ResponseGuard(
            product.parent_asin for product in self._normalized_products
        )
        self.retriever = LexicalRetriever(
            self.connection,
            self._normalized_products,
            retrieval_config(retrieval_name),
        )
        self.dense_config = dense_config(dense_name)
        if dense_model_directory is not None:
            self.dense_config = replace(
                self.dense_config,
                model_directory=str(dense_model_directory),
            )
        if dense_cache_directory is not None:
            self.dense_config = replace(
                self.dense_config,
                cache_directory=str(dense_cache_directory),
            )
        self.dense_retriever: DenseRetriever | None = None
        self._dense_startup_warning: str | None = None
        if self.dense_config.name != "dense_off":
            try:
                encoder = SentenceTransformerEncoder(
                    self.dense_config.model_directory,
                    device=dense_device,
                )
                self.dense_retriever = DenseRetriever(
                    self.dense_config,
                    encoder,
                    expected_asins=tuple(
                        product.parent_asin for product in self._normalized_products
                    ),
                    catalog_sha256=sha256_file(self.catalog_path),
                )
            except Exception as error:
                self._dense_startup_warning = (
                    f"dense_startup_fallback:{type(error).__name__}:{error}"
                )
        self.reranker_config = reranker_config(
            reranker_name,
            depth=reranker_depth,
            batch_size=reranker_batch_size,
            semantic_weight=reranker_semantic_weight,
        )
        if reranker_model_directory is not None:
            self.reranker_config = replace(
                self.reranker_config,
                model_directory=str(reranker_model_directory),
            )
        self.semantic_reranker: SemanticReranker | None = None
        self._reranker_startup_warning: str | None = None
        if self.reranker_config.name != "rerank_off":
            try:
                manifest = load_reranker_manifest(
                    self.reranker_config.model_directory,
                    self.reranker_config.model_id,
                )
                scorer = CrossEncoderScorer(
                    self.reranker_config.model_directory,
                    device=reranker_device,
                )
                self.semantic_reranker = SemanticReranker(
                    self._normalized_products,
                    self.reranker_config,
                    scorer,
                    manifest,
                )
            except Exception as error:
                self._reranker_startup_warning = (
                    f"reranker_startup_fallback:{type(error).__name__}:{error}"
                )
        self.planner = AdaptivePlanner(
            PlannerConfig(
                name=orchestration_name,
                retrieval_name=self.retriever.config.name,
                lexical_depth=self.retriever.config.route_depth,
                fusion_depth=self.retriever.config.fused_depth,
                dense_name=self.dense_config.name,
                reranker_name=self.reranker_config.name,
                rerank_depth=self.reranker_config.depth,
                semantic_rank_weight=self.reranker_config.semantic_weight,
                recommendation_policy=self.policy.config.name,
            )
        )
        self.session_store = SessionStore()
        self.skill_registry = build_skill_registry(
            UnderstandingEngine(self.vocabulary),
            MemoryUpdater(),
            self.retriever,
            self.dense_retriever,
            self.semantic_reranker,
        )
        self._last_traces: dict[str, dict] = {}

    def _build_index(self) -> CatalogVocabulary:
        cursor = self.connection.cursor()
        vocabulary_builder = CatalogVocabularyBuilder()
        cursor.execute(
            "CREATE VIRTUAL TABLE products USING fts5("
            "parent_asin UNINDEXED, title, categories, features, details, store, description, "
            "tokenize='unicode61 remove_diacritics 2')"
        )
        batch: list[tuple[str, str, str, str, str, str, str]] = []
        with self.catalog_path.open(encoding="utf-8") as handle:
            for line in handle:
                product = json.loads(line)
                vocabulary_builder.observe(product)
                self._normalized_products.append(Product.from_source(product))
                batch.append(
                    (
                        str(product["parent_asin"]),
                        _text(product.get("title")),
                        _text(product.get("categories")),
                        _text(product.get("features")),
                        _text(product.get("details")),
                        _text(product.get("store")),
                        _text(product.get("description")),
                    )
                )
                if len(batch) >= 1000:
                    cursor.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)", batch)
                    batch.clear()
        if batch:
            cursor.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)", batch)
        self.connection.commit()
        return vocabulary_builder.build()

    def reset(self, session_id: str, user_profile: dict) -> None:
        self.session_store.reset(session_id, user_profile)
        self._last_traces.pop(session_id, None)

    def respond(
        self,
        session_id: str,
        user_message: str,
        turn: int,
        top_k: int,
    ) -> dict:
        state = self.session_store.get(session_id)
        state.record_turn(turn, user_message)

        understanding: TurnUnderstanding | None = None
        understanding_trace: dict[str, object] = {}
        memory_trace: dict[str, object] = {}
        warnings: list[str] = []
        if self._dense_startup_warning is not None:
            warnings.append(self._dense_startup_warning)
        if self._reranker_startup_warning is not None:
            warnings.append(self._reranker_startup_warning)
        context = SkillContext(state, user_message, turn)
        try:
            understanding_result = self.skill_registry.run("understand_turn", context)
            if not isinstance(understanding_result.output, TurnUnderstanding):
                raise TypeError("understand_turn returned an unexpected output type")
            understanding = understanding_result.output
            understanding_trace = dict(understanding_result.trace)
            context.artifacts["understanding"] = understanding
        except Exception as error:
            warnings.append(f"understanding_fallback:{type(error).__name__}")
        if understanding is not None:
            try:
                memory_result = self.skill_registry.run("update_memory", context)
                memory_trace = dict(memory_result.trace)
            except Exception as error:
                warnings.append(f"memory_fallback:{type(error).__name__}")

        route = understanding.intent.route if understanding else "browsing"
        state.set_initial_route(route)
        context.artifacts["route"] = route
        event_types = tuple(
            event.event_type
            for event in (understanding.parsed_turn.events if understanding else ())
        )
        orchestration_signals = OrchestrationSignals.from_state(
            state.retrieval_view(), route, event_types
        )
        planner_failed = False
        try:
            initial_plan = self.planner.build_initial_plan(orchestration_signals)
            plan_decision = self.planner.decide(initial_plan, initial_plan)
        except Exception as error:
            planner_failed = True
            warnings.append(f"planner_fallback:{type(error).__name__}:{error}")
            plan_decision = self.planner.fallback_decision(
                f"{type(error).__name__}:{error}"
            )
        executed_plan = plan_decision.executed_plan
        selected_retrieval_config = replace(
            retrieval_config(executed_plan.retrieval_name),
            route_depth=executed_plan.lexical_depth,
            fused_depth=executed_plan.fusion_depth,
        )
        context.artifacts["retrieval_config"] = selected_retrieval_config
        context.artifacts["lexical_route_weights"] = executed_plan.route_weights
        context.artifacts["lexical_enabled_routes"] = (
            executed_plan.lexical_enabled_routes or None
        )
        retrieval_trace: dict[str, object] = {}
        try:
            retrieval_skill_result = self.skill_registry.run("retrieve_lexical", context)
            if not isinstance(retrieval_skill_result.output, RetrievalResult):
                raise TypeError("retrieve_lexical returned an unexpected output type")
            lexical_result = retrieval_skill_result.output
            retrieval_trace = dict(retrieval_skill_result.trace)
        except Exception as error:
            warnings.append(f"retrieval_fallback:{type(error).__name__}")
            lexical_result = self._safe_retrieval_fallback(
                user_message, state.retrieval_view(), route, warnings
            )
        if not lexical_result.candidates:
            warnings.append("empty_retrieval_fallback")
            lexical_result = self._safe_retrieval_fallback(
                user_message, state.retrieval_view(), route, warnings
            )

        orchestration_signals = orchestration_signals.with_retrieval(lexical_result)
        if not planner_failed:
            try:
                proposed_plan = self.planner.refine_plan(
                    plan_decision.initial_plan, orchestration_signals
                )
                plan_decision = self.planner.decide(
                    plan_decision.initial_plan, proposed_plan
                )
            except Exception as error:
                warnings.append(
                    f"planner_refine_fallback:{type(error).__name__}:{error}"
                )
                plan_decision = self.planner.fallback_decision(
                    f"{type(error).__name__}:{error}"
                )
        executed_plan = plan_decision.executed_plan
        retrieval_result = lexical_result
        dense_result: DenseResult | None = None
        dense_trace: dict[str, object] = {}
        if executed_plan.dense_enabled and self.dense_retriever is not None:
            try:
                dense_skill_result = self.skill_registry.run("retrieve_dense", context)
                if not isinstance(dense_skill_result.output, DenseResult):
                    raise TypeError("retrieve_dense returned an unexpected output type")
                dense_result = dense_skill_result.output
                dense_trace = dict(dense_skill_result.trace)
                if self.dense_config.fusion_mode == "rescue":
                    retrieval_result = fuse_lexical_and_dense_rescue(
                        lexical_result,
                        dense_result,
                        state=state.retrieval_view(),
                        structured_scorer=self.retriever.structured_scorer,
                        catalog_order=self.retriever.catalog_order,
                        rescue_depth=self.dense_config.rescue_depth,
                    )
                else:
                    fusion_variant = (
                        "dense_only"
                        if self.dense_config.name == "dense_only"
                        else "hybrid_dense"
                    )
                    retrieval_result = fuse_lexical_and_dense(
                        lexical_result,
                        dense_result,
                        route=route,
                        catalog_order=self.retriever.catalog_order,
                        variant=fusion_variant,
                        fused_depth=self.INTERNAL_CANDIDATE_LIMIT,
                        rrf_k=self.dense_config.rrf_k,
                    )
            except Exception as error:
                warnings.append(f"dense_runtime_fallback:{type(error).__name__}:{error}")
        pre_rerank_result = retrieval_result
        rerank_result: RerankResult | None = None
        rerank_trace: dict[str, object] = {}
        if executed_plan.reranker_enabled and self.semantic_reranker is not None:
            context.artifacts["retrieval_result"] = retrieval_result
            context.artifacts["reranker_route"] = route
            context.artifacts["reranker_config"] = replace(
                self.reranker_config,
                depth=executed_plan.rerank_depth,
                semantic_weight=executed_plan.semantic_rank_weight,
            )
            try:
                rerank_skill_result = self.skill_registry.run(
                    "rerank_candidates", context
                )
                if not isinstance(rerank_skill_result.output, RerankResult):
                    raise TypeError("rerank_candidates returned an unexpected output type")
                rerank_result = rerank_skill_result.output
                rerank_trace = dict(rerank_skill_result.trace)
                retrieval_result = rerank_result.retrieval_result
            except Exception as error:
                warnings.append(
                    f"reranker_runtime_fallback:{type(error).__name__}:{error}"
                )
        warnings.extend(retrieval_result.warnings)
        ranked_ids = list(retrieval_result.candidate_ids)
        scores = [-candidate.fused_score for candidate in retrieval_result.candidates]
        recent_override = bool(
            state.revision_history
            and state.revision_history[-1].turn == turn
        )
        signals = RetrievalSignals.from_scores(
            scores,
            self.INTERNAL_CANDIDATE_LIMIT,
            recent_override=recent_override,
        )
        intent_confidence = understanding.intent.confidence if understanding else 0.5
        policy_view = state.retrieval_view()
        try:
            decision: PolicyDecision = self.policy.decide(
                policy_view,
                route,
                intent_confidence,
                signals,
                ranked_ids,
                top_k,
            )
        except Exception as error:
            warnings.append(f"policy_fallback:{type(error).__name__}")
            fallback_policy = RecommendationPolicy(policy_config("always_10"))
            decision = fallback_policy.decide(
                policy_view,
                route,
                intent_confidence,
                signals,
                ranked_ids,
                top_k,
            )
        guarded = self.response_guard.build(
            message=decision.message,
            ask_attribute=decision.clarification.ask_attribute,
            recommendation_ids=decision.recommendation.selected_ids,
            top_k=top_k,
        )
        warnings.extend(guarded.warnings)
        response = guarded.response
        recommendations = cast(list[dict[str, str]], response["recommendations"])
        ask_attribute = response["ask_attribute"]

        if isinstance(ask_attribute, str):
            state.record_clarification(
                turn=turn,
                attribute=ask_attribute,
            )
        state.record_shown_products(
            turn=turn,
            ranked_ids=(item["parent_asin"] for item in recommendations),
        )
        view = state.retrieval_view()
        self._last_traces[session_id] = {
            "candidate_ids": ranked_ids,
            "route_candidate_ids": {
                result.name: list(result.candidate_ids[: self.INTERNAL_CANDIDATE_LIMIT])
                for result in retrieval_result.routes
            },
            "compiled_queries": {
                query.name: list(query.terms) for query in retrieval_result.queries
            },
            "candidate_evidence": [
                {
                    "parent_asin": candidate.parent_asin,
                    "fused_score": candidate.fused_score,
                    "route_ranks": dict(candidate.route_ranks),
                    "route_contributions": dict(candidate.route_contributions),
                    "compatibility_score": candidate.compatibility_score,
                    "matched_constraints": list(candidate.matched_constraints),
                    "contradicted_constraints": list(candidate.contradicted_constraints),
                }
                for candidate in retrieval_result.candidates[:20]
            ],
            "retrieval_name": retrieval_result.config_name,
            "retrieval_skill": retrieval_trace,
            "lexical_retrieval_name": lexical_result.config_name,
            "dense_name": self.dense_config.name,
            "dense_skill": dense_trace,
            "dense_query": dense_result.query.text if dense_result else None,
            "dense_queries": (
                {item.name: item.query.text for item in dense_result.routes}
                if dense_result else {}
            ),
            "dense_candidate_ids": (
                list(dense_result.candidate_ids[: self.INTERNAL_CANDIDATE_LIMIT])
                if dense_result else []
            ),
            "dense_candidate_scores": (
                list(dense_result.scores[: self.INTERNAL_CANDIDATE_LIMIT])
                if dense_result else []
            ),
            "reranker_name": self.reranker_config.name,
            "reranker_skill": rerank_trace,
            "rerank_query": rerank_result.query.text if rerank_result else None,
            "pre_rerank_candidate_ids": list(pre_rerank_result.candidate_ids),
            "rerank_details": [
                {
                    "parent_asin": item.parent_asin,
                    "original_rank": item.original_rank,
                    "semantic_rank": item.semantic_rank,
                    "semantic_score": item.semantic_score,
                    "retrieval_contribution": item.retrieval_contribution,
                    "semantic_contribution": item.semantic_contribution,
                    "compatibility_contribution": item.compatibility_contribution,
                    "contradiction_penalty": item.contradiction_penalty,
                    "final_score": item.final_score,
                }
                for item in (rerank_result.candidates if rerank_result else ())
            ],
            "inferred_route": understanding.intent.route if understanding else None,
            "intent_confidence": intent_confidence,
            "recommendation_confidence": decision.confidence.score,
            "confidence": decision.confidence.score,
            "confidence_level": decision.confidence.level,
            "confidence_components": dict(decision.confidence.components),
            "over_general": decision.confidence.over_general,
            "active_slots": [
                {
                    "name": name,
                    "match_mode": slot.match_mode,
                    "values": [value.normalized_value for value in slot.values],
                    "strengths": [value.strength for value in slot.values],
                }
                for name, slot in view.active_slots.items()
            ],
            "events": understanding_trace.get("events", ()),
            "route_reasons": understanding_trace.get("reasons", ()),
            "memory_actions": memory_trace.get("actions", ()),
            "search_revision": view.search_revision,
            "context_version": view.context_version,
            "ask_attribute": ask_attribute,
            "clarification_utility": decision.clarification.utility,
            "recommendation_limit": decision.recommendation.limit,
            "policy_name": self.policy.config.name,
            "policy_version": self.policy.config.version,
            "policy_reasons": decision.reasons,
            "retrieval_signals": {
                "candidate_count": signals.candidate_count,
                "internal_limit": signals.internal_limit,
                "score_separation": signals.score_separation,
                "saturated": signals.saturated,
                "recent_override": signals.recent_override,
            },
            "orchestration": plan_decision.as_trace(),
            "orchestration_signals": {
                "route": orchestration_signals.route,
                "turn_number": orchestration_signals.turn_number,
                "active_slot_count": orchestration_signals.active_slot_count,
                "hard_constraint_count": orchestration_signals.hard_constraint_count,
                "is_override": orchestration_signals.is_override,
                "has_no_preference": orchestration_signals.has_no_preference,
                "candidate_count": orchestration_signals.candidate_count,
                "route_count": orchestration_signals.route_count,
                "score_margin": orchestration_signals.score_margin,
                "constraint_coverage": orchestration_signals.constraint_coverage,
            },
            "fallback_used": bool(warnings),
            "warnings": warnings,
        }
        return response

    def _safe_retrieval_fallback(
        self,
        user_message: str,
        state_view: StateView,
        route: str,
        warnings: list[str],
    ) -> RetrievalResult:
        try:
            result = self.retriever.fallback(user_message, state_view, route)
            if result.candidates:
                return result
        except Exception as error:
            warnings.append(f"single_bm25_fallback:{type(error).__name__}")
        try:
            return self.retriever.catalog_fallback(state_view)
        except Exception as error:
            warnings.append(f"catalog_fallback:{type(error).__name__}")
            return self.retriever.empty_result()

    def get_last_trace(self, session_id: str) -> dict:
        return dict(self._last_traces.get(session_id, {}))
