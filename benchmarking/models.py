from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BenchmarkConfig:
    """Inputs that must be fixed for a reproducible benchmark run."""

    experiment_name: str
    catalog_path: str = "data/catalog.jsonl"
    dataset_path: str = "data/public_set.jsonl"
    output_root: str = "experiments/runs"
    split: str = "development"
    seed: int = 42
    sample_id: str | None = None
    sample_limit: int | None = None
    agent_variant: str = "always_10"
    retrieval_variant: str = "multi_route_structured"
    dense_variant: str = "dense_off"
    reranker_variant: str = "minilm_l4_blended"
    reranker_depth: int = 60
    reranker_batch_size: int = 32
    reranker_semantic_weight: float = 0.25
    orchestration_variant: str = "adaptive_cutoff"


@dataclass
class TurnRecord:
    """What happened during one call to Agent.respond."""

    experiment_id: str
    sample_id: str
    session_id: str
    scenario_type: str
    turn: int
    user_message: str
    response_message: str
    ask_attribute: str | None
    recommendation_ids: list[str]
    target_rank: int | None
    score_eligible: bool
    latency_ms: float
    warnings: list[str] = field(default_factory=list)
    exception: str | None = None
    candidate_ids: list[str] | None = None
    inferred_route: str | None = None
    active_slots: list[dict] | None = None
    recommendation_limit: int | None = None
    confidence: float | None = None
    intent_confidence: float | None = None
    recommendation_confidence: float | None = None
    confidence_components: dict[str, float] | None = None
    clarification_utility: float | None = None
    policy_reasons: list[str] | None = None
    retrieval_name: str | None = None
    route_candidate_ids: dict[str, list[str]] | None = None
    route_target_ranks: dict[str, int] | None = None
    compiled_queries: dict[str, list[str]] | None = None
    candidate_evidence: list[dict] | None = None
    dense_name: str | None = None
    dense_query: str | None = None
    dense_candidate_ids: list[str] | None = None
    dense_candidate_scores: list[float] | None = None
    dense_target_rank: int | None = None
    dense_skill: dict | None = None
    reranker_name: str | None = None
    rerank_query: str | None = None
    pre_rerank_candidate_ids: list[str] | None = None
    pre_rerank_target_rank: int | None = None
    post_rerank_target_rank: int | None = None
    rerank_details: list[dict] | None = None
    reranker_skill: dict | None = None
    orchestration: dict | None = None
    orchestration_signals: dict | None = None
    fallback_used: bool = False
    prompt_tokens: int = 0
    completion_tokens: int = 0


@dataclass
class SessionRecord:
    """Scored result and diagnostics for one simulated session."""

    sample_id: str
    scenario_type: str
    hit: bool
    first_hit_turn: int | None
    best_rank: int | None
    reciprocal_rank: float
    turn_count: int
    latency_ms: float
    candidate_best_rank: int | None = None
