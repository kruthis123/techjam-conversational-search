from __future__ import annotations

import hashlib
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from evaluator.local_evaluator import (
    ALLOWED_ATTRIBUTES,
    MAX_TURNS,
    TOP_K,
    catalog_index,
    coarse_category,
    customer_reply,
    initial_message,
    load_jsonl,
    materialize_hidden_fields,
    normalize_recommendations,
)

from .models import BenchmarkConfig, SessionRecord, TurnRecord
from .reporting import build_summary, write_artifacts


AgentFactory = Callable[[str], object]


def _peak_rss_mb() -> float | None:
    try:
        import resource

        value = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    except (ImportError, OSError, ValueError):
        return None
    divisor = 1024 * 1024 if sys.platform == "darwin" else 1024
    return round(value / divisor, 6)


def _path_size_bytes(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    if not path.is_dir():
        return 0
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def _runtime_artifact_sizes(agent: object, catalog_path: str) -> dict[str, object]:
    paths: dict[str, Path] = {"catalog": Path(catalog_path)}
    reranker = getattr(agent, "semantic_reranker", None)
    reranker_config = getattr(agent, "reranker_config", None)
    if reranker is not None and reranker_config is not None:
        paths["reranker_model"] = Path(str(reranker_config.model_directory))
    dense_retriever = getattr(agent, "dense_retriever", None)
    dense_config = getattr(agent, "dense_config", None)
    if dense_retriever is not None and dense_config is not None:
        paths["dense_model"] = Path(str(dense_config.model_directory))
        paths["dense_cache"] = Path(str(dense_config.cache_directory))

    sizes = {
        name: _path_size_bytes(path)
        for name, path in paths.items()
    }
    return {
        "bytes": sizes,
        "megabytes": {
            name: round(size / (1024 * 1024), 6)
            for name, size in sizes.items()
        },
        "total_bytes": sum(sizes.values()),
        "total_megabytes": round(sum(sizes.values()) / (1024 * 1024), 6),
    }


def validate_response(response: object) -> list[str]:
    """Return contract warnings without raising or changing the response."""
    if not isinstance(response, dict):
        return ["response_not_object"]

    warnings: list[str] = []
    for name in ("message", "ask_attribute", "recommendations"):
        if name not in response:
            warnings.append(f"missing_{name}")
    unknown_fields = set(response) - {"message", "ask_attribute", "recommendations", "usage"}
    if unknown_fields:
        warnings.append("unknown_response_fields")

    if not isinstance(response.get("message"), str):
        warnings.append("message_not_string")

    ask_attribute = response.get("ask_attribute")
    if ask_attribute is not None and ask_attribute not in ALLOWED_ATTRIBUTES:
        warnings.append("invalid_ask_attribute")

    recommendations = response.get("recommendations")
    if not isinstance(recommendations, list):
        warnings.append("recommendations_not_list")
    else:
        if len(recommendations) > 100:
            warnings.append("too_many_recommendations")
        for item in recommendations:
            if not isinstance(item, dict) or not isinstance(item.get("parent_asin"), str):
                warnings.append("invalid_recommendation_item")
                break
            if set(item) - {"parent_asin", "score"}:
                warnings.append("unknown_recommendation_fields")
                break
            if "score" in item and not isinstance(item["score"], (int, float)):
                warnings.append("invalid_recommendation_score")
                break

    usage = response.get("usage")
    if usage is not None:
        if not isinstance(usage, dict):
            warnings.append("usage_not_object")
        else:
            for name in ("prompt_tokens", "completion_tokens"):
                value = usage.get(name)
                if not isinstance(value, int) or value < 0:
                    warnings.append(f"invalid_{name}")
    return warnings


def select_samples(samples: list[dict], config: BenchmarkConfig) -> list[dict]:
    """Select a deterministic development, lockbox, all, or single-sample set."""
    if config.sample_id:
        selected = [item for item in samples if item.get("sample_id") == config.sample_id]
        if not selected:
            raise ValueError(f"Unknown sample_id: {config.sample_id}")
        return selected

    if config.split == "all":
        return _limit_samples(samples, config)
    if config.split not in {"development", "lockbox"}:
        raise ValueError(f"Unsupported split: {config.split}")

    lockbox_ids: set[str] = set()
    by_scenario: dict[str, list[dict]] = defaultdict(list)
    for sample in samples:
        by_scenario[str(sample["scenario_type"])].append(sample)

    for scenario_samples in by_scenario.values():
        ranked = sorted(
            scenario_samples,
            key=lambda item: hashlib.sha256(
                f"{config.seed}:{item['sample_id']}".encode("utf-8")
            ).hexdigest(),
        )
        lockbox_count = max(1, round(len(ranked) * 0.20))
        lockbox_ids.update(str(item["sample_id"]) for item in ranked[:lockbox_count])

    want_lockbox = config.split == "lockbox"
    selected = [
        sample
        for sample in samples
        if (str(sample["sample_id"]) in lockbox_ids) == want_lockbox
    ]
    return _limit_samples(selected, config)


def _limit_samples(samples: list[dict], config: BenchmarkConfig) -> list[dict]:
    if config.sample_limit is None:
        return samples
    if config.sample_limit <= 0:
        raise ValueError("sample_limit must be positive")
    return sorted(
        samples,
        key=lambda item: hashlib.sha256(
            f"pilot:{config.seed}:{item['sample_id']}".encode("utf-8")
        ).hexdigest(),
    )[: config.sample_limit]


def _safe_agent_trace(agent: object, session_id: str, catalog_ids: set[str]) -> dict:
    """Read optional Agent diagnostics without making them part of the API response."""
    getter = getattr(agent, "get_last_trace", None)
    if not callable(getter):
        return {}
    try:
        trace = getter(session_id)
    except Exception:
        return {"warnings": ["trace_collection_failed"]}
    if not isinstance(trace, dict):
        return {"warnings": ["trace_not_object"]}

    raw_candidates = trace.get("candidate_ids")
    candidate_ids: list[str] | None = None
    if isinstance(raw_candidates, list):
        candidate_ids = []
        seen: set[str] = set()
        for item in raw_candidates:
            parent_asin = str(item).strip()
            if parent_asin and parent_asin in catalog_ids and parent_asin not in seen:
                seen.add(parent_asin)
                candidate_ids.append(parent_asin)

    route_candidate_ids: dict[str, list[str]] | None = None
    raw_routes = trace.get("route_candidate_ids")
    if isinstance(raw_routes, dict):
        route_candidate_ids = {}
        for raw_name, raw_ids in raw_routes.items():
            if not isinstance(raw_ids, list):
                continue
            route_ids: list[str] = []
            seen: set[str] = set()
            for item in raw_ids:
                parent_asin = str(item).strip()
                if parent_asin and parent_asin in catalog_ids and parent_asin not in seen:
                    route_ids.append(parent_asin)
                    seen.add(parent_asin)
            route_candidate_ids[str(raw_name)] = route_ids

    dense_candidate_ids: list[str] | None = None
    raw_dense_ids = trace.get("dense_candidate_ids")
    if isinstance(raw_dense_ids, list):
        dense_candidate_ids = []
        seen = set()
        for item in raw_dense_ids:
            parent_asin = str(item).strip()
            if parent_asin and parent_asin in catalog_ids and parent_asin not in seen:
                dense_candidate_ids.append(parent_asin)
                seen.add(parent_asin)

    dense_candidate_scores: list[float] | None = None
    raw_dense_scores = trace.get("dense_candidate_scores")
    if isinstance(raw_dense_scores, list):
        dense_candidate_scores = [
            float(value) for value in raw_dense_scores if isinstance(value, (int, float))
        ]

    pre_rerank_candidate_ids: list[str] | None = None
    raw_pre_rerank = trace.get("pre_rerank_candidate_ids")
    if isinstance(raw_pre_rerank, list):
        pre_rerank_candidate_ids = []
        seen = set()
        for item in raw_pre_rerank:
            parent_asin = str(item).strip()
            if parent_asin and parent_asin in catalog_ids and parent_asin not in seen:
                pre_rerank_candidate_ids.append(parent_asin)
                seen.add(parent_asin)

    return {
        "candidate_ids": candidate_ids,
        "inferred_route": trace.get("inferred_route"),
        "active_slots": trace.get("active_slots"),
        "recommendation_limit": trace.get("recommendation_limit"),
        "confidence": trace.get("confidence"),
        "intent_confidence": trace.get("intent_confidence"),
        "recommendation_confidence": trace.get("recommendation_confidence"),
        "confidence_components": trace.get("confidence_components"),
        "clarification_utility": trace.get("clarification_utility"),
        "policy_reasons": trace.get("policy_reasons"),
        "retrieval_name": trace.get("retrieval_name"),
        "route_candidate_ids": route_candidate_ids,
        "compiled_queries": trace.get("compiled_queries"),
        "candidate_evidence": trace.get("candidate_evidence"),
        "dense_name": trace.get("dense_name"),
        "dense_query": trace.get("dense_query"),
        "dense_candidate_ids": dense_candidate_ids,
        "dense_candidate_scores": dense_candidate_scores,
        "dense_skill": trace.get("dense_skill"),
        "reranker_name": trace.get("reranker_name"),
        "rerank_query": trace.get("rerank_query"),
        "pre_rerank_candidate_ids": pre_rerank_candidate_ids,
        "rerank_details": trace.get("rerank_details"),
        "reranker_skill": trace.get("reranker_skill"),
        "orchestration": trace.get("orchestration"),
        "orchestration_signals": trace.get("orchestration_signals"),
        "fallback_used": bool(trace.get("fallback_used", False)),
        "warnings": trace.get("warnings", []),
    }


def _session_id(experiment_id: str, sample_id: str) -> str:
    value = hashlib.sha256(f"{experiment_id}\0{sample_id}".encode("utf-8")).hexdigest()
    return f"bench_{value[:24]}"


def _token_usage(response: dict) -> tuple[int, int]:
    usage = response.get("usage")
    if not isinstance(usage, dict):
        return 0, 0
    prompt = usage.get("prompt_tokens")
    completion = usage.get("completion_tokens")
    return (
        prompt if isinstance(prompt, int) and prompt >= 0 else 0,
        completion if isinstance(completion, int) and completion >= 0 else 0,
    )


def run_session(
    agent: object,
    sample: dict,
    catalog_ids: set[str],
    categories: dict[str, list[str]],
    products: dict[str, dict],
    experiment_id: str,
) -> tuple[SessionRecord, list[TurnRecord]]:
    """Run one session with the same conversation and scoring rules as the evaluator."""
    sample_id = str(sample["sample_id"])
    scenario_type = str(sample["scenario_type"])
    session_id = _session_id(experiment_id, sample_id)
    target = str(sample["ground_truth"]["parent_asin"])

    agent.reset(session_id, sample["user_profile"])
    intent_card, behavior = materialize_hidden_fields(sample, products)
    effective_sample = {**sample, "intent_card": intent_card, "behavior": behavior}

    disclosed: set[str] = set()
    boundary_used = False
    override_applied = scenario_type != "intent_override"
    user_message = initial_message(
        effective_sample,
        coarse_category(categories.get(target, [])),
        disclosed,
    )

    turns: list[TurnRecord] = []
    hit_turn: int | None = None
    best_rank: int | None = None
    candidate_best_rank: int | None = None

    for turn in range(1, MAX_TURNS + 1):
        exception: str | None = None
        started = time.perf_counter_ns()
        try:
            raw_response = agent.respond(session_id, user_message, turn, TOP_K)
        except Exception as exc:  # The official evaluator also converts exceptions to misses.
            exception = f"{type(exc).__name__}: {exc}"
            raw_response = None
        latency_ms = (time.perf_counter_ns() - started) / 1_000_000

        warnings = validate_response(raw_response)
        if not isinstance(raw_response, dict) or not isinstance(raw_response.get("message"), str):
            response = {"message": "", "ask_attribute": None, "recommendations": []}
        else:
            response = raw_response

        ranked = normalize_recommendations(response.get("recommendations"), catalog_ids)
        target_rank = ranked.index(target) + 1 if target in ranked else None
        prompt_tokens, completion_tokens = _token_usage(response)

        trace = _safe_agent_trace(agent, session_id, catalog_ids)
        trace_warnings = trace.get("warnings")
        if isinstance(trace_warnings, list):
            warnings.extend(str(item) for item in trace_warnings)
        candidate_ids = trace.get("candidate_ids")
        route_candidate_ids = trace.get("route_candidate_ids")
        route_target_ranks = {
            name: ids.index(target) + 1
            for name, ids in (route_candidate_ids or {}).items()
            if target in ids
        }
        dense_candidate_ids = trace.get("dense_candidate_ids")
        dense_target_rank = (
            dense_candidate_ids.index(target) + 1
            if isinstance(dense_candidate_ids, list) and target in dense_candidate_ids
            else None
        )
        pre_rerank_candidate_ids = trace.get("pre_rerank_candidate_ids")
        pre_rerank_target_rank = (
            pre_rerank_candidate_ids.index(target) + 1
            if isinstance(pre_rerank_candidate_ids, list)
            and target in pre_rerank_candidate_ids
            else None
        )
        post_rerank_target_rank = (
            candidate_ids.index(target) + 1
            if isinstance(candidate_ids, list) and target in candidate_ids
            else None
        )
        if override_applied and isinstance(candidate_ids, list) and target in candidate_ids:
            rank = candidate_ids.index(target) + 1
            candidate_best_rank = (
                rank if candidate_best_rank is None else min(candidate_best_rank, rank)
            )

        turns.append(
            TurnRecord(
                experiment_id=experiment_id,
                sample_id=sample_id,
                session_id=session_id,
                scenario_type=scenario_type,
                turn=turn,
                user_message=user_message,
                response_message=str(response["message"]),
                ask_attribute=response.get("ask_attribute"),
                recommendation_ids=ranked,
                target_rank=target_rank,
                score_eligible=override_applied,
                latency_ms=latency_ms,
                warnings=list(dict.fromkeys(warnings)),
                exception=exception,
                candidate_ids=candidate_ids,
                inferred_route=trace.get("inferred_route"),
                active_slots=trace.get("active_slots"),
                recommendation_limit=trace.get("recommendation_limit"),
                confidence=trace.get("confidence"),
                intent_confidence=trace.get("intent_confidence"),
                recommendation_confidence=trace.get("recommendation_confidence"),
                confidence_components=trace.get("confidence_components"),
                clarification_utility=trace.get("clarification_utility"),
                policy_reasons=trace.get("policy_reasons"),
                retrieval_name=trace.get("retrieval_name"),
                route_candidate_ids=route_candidate_ids,
                route_target_ranks=route_target_ranks,
                compiled_queries=trace.get("compiled_queries"),
                candidate_evidence=trace.get("candidate_evidence"),
                dense_name=trace.get("dense_name"),
                dense_query=trace.get("dense_query"),
                dense_candidate_ids=dense_candidate_ids,
                dense_candidate_scores=trace.get("dense_candidate_scores"),
                dense_target_rank=dense_target_rank,
                dense_skill=trace.get("dense_skill"),
                reranker_name=trace.get("reranker_name"),
                rerank_query=trace.get("rerank_query"),
                pre_rerank_candidate_ids=pre_rerank_candidate_ids,
                pre_rerank_target_rank=pre_rerank_target_rank,
                post_rerank_target_rank=post_rerank_target_rank,
                rerank_details=trace.get("rerank_details"),
                reranker_skill=trace.get("reranker_skill"),
                orchestration=trace.get("orchestration"),
                orchestration_signals=trace.get("orchestration_signals"),
                fallback_used=bool(trace.get("fallback_used", False)),
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )
        )

        if override_applied and target_rank is not None:
            hit_turn = turn
            best_rank = target_rank
            break
        if turn == MAX_TURNS:
            break

        override = behavior.get("override") or {}
        if not override_applied and turn + 1 == int(override.get("turn", 3)):
            override_applied = True
            new_value = str(override.get("new_value", ""))
            if new_value:
                disclosed.add(new_value)
            user_message = str(
                override.get("message", "Actually, please ignore my earlier preference.")
            )
        else:
            user_message, boundary_used = customer_reply(
                effective_sample,
                response.get("ask_attribute"),
                disclosed,
                boundary_used,
            )

    session = SessionRecord(
        sample_id=sample_id,
        scenario_type=scenario_type,
        hit=hit_turn is not None,
        first_hit_turn=hit_turn,
        best_rank=best_rank,
        reciprocal_rank=0.0 if best_rank is None else 1.0 / best_rank,
        turn_count=len(turns),
        latency_ms=sum(item.latency_ms for item in turns),
        candidate_best_rank=candidate_best_rank,
    )
    return session, turns


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", value).strip("_")
    return cleaned or "experiment"


def run_benchmark(
    config: BenchmarkConfig,
    agent_factory: AgentFactory | None = None,
) -> tuple[dict, Path]:
    """Run a benchmark and write a self-contained experiment artifact directory."""
    benchmark_started = time.perf_counter_ns()
    initial_peak_rss_mb = _peak_rss_mb()
    if agent_factory is None:
        from starter.agent import Agent

        def default_agent_factory(catalog_path: str) -> object:
            return Agent(
                catalog_path,
                policy_name=config.agent_variant,
                retrieval_name=config.retrieval_variant,
                dense_name=config.dense_variant,
                reranker_name=config.reranker_variant,
                reranker_depth=config.reranker_depth,
                reranker_batch_size=config.reranker_batch_size,
                reranker_semantic_weight=config.reranker_semantic_weight,
                orchestration_name=config.orchestration_variant,
            )

        agent_factory = default_agent_factory

    all_samples = load_jsonl(config.dataset_path)
    samples = select_samples(all_samples, config)
    catalog_ids, categories, products = catalog_index(config.catalog_path)

    created_at = datetime.now(timezone.utc)
    timestamp = created_at.strftime("%Y%m%dT%H%M%SZ")
    experiment_id = f"{timestamp}_{_slug(config.experiment_name)}"

    startup_started = time.perf_counter_ns()
    agent = agent_factory(config.catalog_path)
    startup_ms = (time.perf_counter_ns() - startup_started) / 1_000_000
    startup_peak_rss_mb = _peak_rss_mb()

    sessions: list[SessionRecord] = []
    turns: list[TurnRecord] = []
    for sample in samples:
        session, session_turns = run_session(
            agent,
            sample,
            catalog_ids,
            categories,
            products,
            experiment_id,
        )
        sessions.append(session)
        turns.extend(session_turns)

    summary = build_summary(sessions, turns)
    summary["startup_ms"] = round(startup_ms, 6)
    final_peak_rss_mb = _peak_rss_mb()
    summary["performance"] = {
        "wall_runtime_ms": round(
            (time.perf_counter_ns() - benchmark_started) / 1_000_000,
            6,
        ),
        "startup_ms": round(startup_ms, 6),
        "initial_peak_rss_mb": initial_peak_rss_mb,
        "startup_peak_rss_mb": startup_peak_rss_mb,
        "final_peak_rss_mb": final_peak_rss_mb,
        "startup_peak_growth_mb": (
            None
            if initial_peak_rss_mb is None or startup_peak_rss_mb is None
            else round(max(0.0, startup_peak_rss_mb - initial_peak_rss_mb), 6)
        ),
        "runtime_peak_growth_mb": (
            None
            if startup_peak_rss_mb is None or final_peak_rss_mb is None
            else round(max(0.0, final_peak_rss_mb - startup_peak_rss_mb), 6)
        ),
        "artifact_sizes": _runtime_artifact_sizes(agent, config.catalog_path),
        "external_api_calls": 0,
        "estimated_external_cost_usd": 0.0,
    }
    run_directory = write_artifacts(
        config,
        experiment_id,
        created_at,
        samples,
        sessions,
        turns,
        summary,
    )
    return summary, run_directory
