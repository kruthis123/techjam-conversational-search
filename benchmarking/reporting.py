from __future__ import annotations

import hashlib
import json
import math
import platform
import statistics
import subprocess
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from evaluator.local_evaluator import metric_summary

from .models import BenchmarkConfig, SessionRecord, TurnRecord


CANDIDATE_RECALL_KS = (50, 100, 200)
STABILITY_FOLD_COUNT = 5


def _technical_score(metrics: dict) -> float:
    efficiency = max(0.0, min(1.0, (11.0 - float(metrics["mttc"])) / 10.0))
    return round(
        0.50 * metrics["hit_rate_at_10"]
        + 0.30 * metrics["mrr"]
        + 0.20 * efficiency,
        6,
    )


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(len(ordered) * fraction) - 1)
    return round(ordered[index], 6)


def _candidate_metrics(sessions: list[SessionRecord], turns: list[TurnRecord]) -> dict:
    by_sample: dict[str, list[TurnRecord]] = defaultdict(list)
    for turn in turns:
        by_sample[turn.sample_id].append(turn)

    result: dict[str, dict] = {}
    for k in CANDIDATE_RECALL_KS:
        measured = 0
        hits = 0
        for session in sessions:
            eligible = [
                turn
                for turn in by_sample[session.sample_id]
                if turn.score_eligible and turn.candidate_ids is not None
            ]
            if not eligible:
                continue
            measured += 1
            if session.candidate_best_rank is not None and session.candidate_best_rank <= k:
                hits += 1
        result[f"recall_at_{k}"] = {
            "measured_sessions": measured,
            "value": None if measured == 0 else round(hits / measured, 6),
        }
    return result


def _stability_fold_metrics(sessions: list[SessionRecord]) -> dict:
    """Report deterministic, target-independent slices for robustness checks."""
    folds: dict[int, list[dict]] = defaultdict(list)
    for session in sessions:
        digest = hashlib.sha256(f"stability:{session.sample_id}".encode()).digest()
        fold = int.from_bytes(digest[:4], "big") % STABILITY_FOLD_COUNT
        folds[fold].append(asdict(session))

    result: dict[str, dict] = {}
    for fold in range(STABILITY_FOLD_COUNT):
        items = folds.get(fold, [])
        if not items:
            continue
        metrics = metric_summary(items)
        result[str(fold)] = {
            **metrics,
            "recommended_technical_score": _technical_score(metrics),
        }
    return result


def _route_candidate_metrics(sessions: list[SessionRecord], turns: list[TurnRecord]) -> dict:
    by_sample: dict[str, list[TurnRecord]] = defaultdict(list)
    route_names: set[str] = set()
    for turn in turns:
        by_sample[turn.sample_id].append(turn)
        route_names.update((turn.route_candidate_ids or {}).keys())

    result: dict[str, dict] = {}
    for route_name in sorted(route_names):
        measured = 0
        hits = 0
        for session in sessions:
            eligible = [
                turn
                for turn in by_sample[session.sample_id]
                if turn.score_eligible
                and route_name in (turn.route_candidate_ids or {})
            ]
            if not eligible:
                continue
            measured += 1
            if any(
                (turn.route_target_ranks or {}).get(route_name, 10**9) <= 200
                for turn in eligible
            ):
                hits += 1
        result[route_name] = {
            "measured_sessions": measured,
            "recall_at_200": None if measured == 0 else round(hits / measured, 6),
        }
    return result


def _route_union_metrics(sessions: list[SessionRecord], turns: list[TurnRecord]) -> dict:
    by_sample: dict[str, list[TurnRecord]] = defaultdict(list)
    for turn in turns:
        if turn.score_eligible and turn.route_candidate_ids:
            by_sample[turn.sample_id].append(turn)

    measured = 0
    lexical_hits = 0
    combined_hits = 0
    dense_only_additions = 0
    for session in sessions:
        eligible = by_sample.get(session.sample_id, [])
        if not eligible:
            continue
        measured += 1
        lexical_hit = any(
            any(
                rank <= 200
                for name, rank in (turn.route_target_ranks or {}).items()
                if not name.startswith("dense")
            )
            for turn in eligible
        )
        dense_hit = any(
            any(
                rank <= 200
                for name, rank in (turn.route_target_ranks or {}).items()
                if name.startswith("dense")
            )
            for turn in eligible
        )
        lexical_hits += lexical_hit
        combined_hits += lexical_hit or dense_hit
        dense_only_additions += dense_hit and not lexical_hit

    def ratio(value: int) -> float | None:
        return None if measured == 0 else round(value / measured, 6)

    return {
        "measured_sessions": measured,
        "lexical_recall_at_200": ratio(lexical_hits),
        "combined_recall_at_200": ratio(combined_hits),
        "dense_only_addition_rate": ratio(dense_only_additions),
    }


def _dense_diagnostics(turns: list[TurnRecord]) -> dict:
    dense_turns = [turn for turn in turns if turn.dense_skill]
    encode_latencies = [
        float(turn.dense_skill["encode_latency_ms"])
        for turn in dense_turns
        if isinstance(turn.dense_skill, dict)
        and isinstance(turn.dense_skill.get("encode_latency_ms"), (int, float))
    ]
    return {
        "turn_count": len(dense_turns),
        "target_found_turn_count": sum(turn.dense_target_rank is not None for turn in dense_turns),
        "mean_encode_latency_ms": (
            None if not encode_latencies else round(statistics.fmean(encode_latencies), 6)
        ),
        "model_ids": sorted(
            {
                str(turn.dense_skill["model_id"])
                for turn in dense_turns
                if isinstance(turn.dense_skill, dict) and turn.dense_skill.get("model_id")
            }
        ),
        "model_revisions": sorted(
            {
                str(turn.dense_skill["model_revision"])
                for turn in dense_turns
                if isinstance(turn.dense_skill, dict)
                and turn.dense_skill.get("model_revision")
            }
        ),
    }


def _reranker_diagnostics(turns: list[TurnRecord]) -> dict:
    reranked = [turn for turn in turns if turn.reranker_skill]
    latencies = [
        float(turn.reranker_skill["inference_latency_ms"])
        for turn in reranked
        if isinstance(turn.reranker_skill, dict)
        and isinstance(turn.reranker_skill.get("inference_latency_ms"), (int, float))
    ]
    movements = [
        turn.pre_rerank_target_rank - turn.post_rerank_target_rank
        for turn in reranked
        if turn.pre_rerank_target_rank is not None
        and turn.post_rerank_target_rank is not None
    ]
    return {
        "turn_count": len(reranked),
        "mean_inference_latency_ms": (
            None if not latencies else round(statistics.fmean(latencies), 6)
        ),
        "mean_target_rank_improvement": (
            None if not movements else round(statistics.fmean(movements), 6)
        ),
        "target_promoted_turn_count": sum(value > 0 for value in movements),
        "target_demoted_turn_count": sum(value < 0 for value in movements),
        "model_ids": sorted(
            {
                str(turn.reranker_skill["model_id"])
                for turn in reranked
                if isinstance(turn.reranker_skill, dict)
                and turn.reranker_skill.get("model_id")
            }
        ),
        "model_revisions": sorted(
            {
                str(turn.reranker_skill["model_revision"])
                for turn in reranked
                if isinstance(turn.reranker_skill, dict)
                and turn.reranker_skill.get("model_revision")
            }
        ),
    }


def _orchestration_diagnostics(turns: list[TurnRecord]) -> dict:
    plans = [turn.orchestration for turn in turns if turn.orchestration]
    proposed_modes: Counter[str] = Counter()
    executed_modes: Counter[str] = Counter()
    reranker_calls_avoided = 0
    executed_depths: list[int] = []
    shadow_turns = 0
    planner_fallbacks = 0
    for item in plans:
        if not isinstance(item, dict):
            continue
        proposed = item.get("proposed_plan")
        executed = item.get("executed_plan")
        if isinstance(proposed, dict):
            proposed_modes[str(proposed.get("mode", "unknown"))] += 1
        if isinstance(executed, dict):
            executed_modes[str(executed.get("mode", "unknown"))] += 1
            depth = executed.get("rerank_depth")
            if isinstance(depth, int) and bool(executed.get("reranker_enabled")):
                executed_depths.append(depth)
            if (
                isinstance(proposed, dict)
                and bool(proposed.get("reranker_enabled")) is False
                and bool(executed.get("reranker_enabled")) is False
            ):
                reranker_calls_avoided += 1
        shadow_turns += bool(item.get("shadow"))
        planner_fallbacks += item.get("fallback_reason") is not None
    return {
        "measured_turns": len(plans),
        "proposed_mode_counts": dict(sorted(proposed_modes.items())),
        "executed_mode_counts": dict(sorted(executed_modes.items())),
        "shadow_turns": shadow_turns,
        "planner_fallbacks": planner_fallbacks,
        "reranker_calls_avoided": reranker_calls_avoided,
        "mean_executed_rerank_depth": (
            None
            if not executed_depths
            else round(statistics.fmean(executed_depths), 6)
        ),
    }


def build_summary(sessions: list[SessionRecord], turns: list[TurnRecord]) -> dict:
    """Aggregate official scores and participant-owned diagnostics."""
    session_dicts = [asdict(item) for item in sessions]
    overall = metric_summary(session_dicts)
    efficiency = max(0.0, min(1.0, (11.0 - float(overall["mttc"])) / 10.0))
    technical_score = _technical_score(overall)

    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in session_dicts:
        grouped[str(item["scenario_type"])].append(item)

    latencies = [item.latency_ms for item in turns]
    recommendation_counts = Counter(len(item.recommendation_ids) for item in turns)
    question_counts = Counter(str(item.ask_attribute) for item in turns)

    return {
        **overall,
        "efficiency": round(efficiency, 6),
        "recommended_technical_score": technical_score,
        "scenario_metrics": {
            name: metric_summary(items) for name, items in sorted(grouped.items())
        },
        "stability_fold_metrics": _stability_fold_metrics(sessions),
        "candidate_metrics": _candidate_metrics(sessions, turns),
        "route_candidate_metrics": _route_candidate_metrics(sessions, turns),
        "route_union_metrics": _route_union_metrics(sessions, turns),
        "dense_diagnostics": _dense_diagnostics(turns),
        "reranker_diagnostics": _reranker_diagnostics(turns),
        "orchestration_diagnostics": _orchestration_diagnostics(turns),
        "latency_ms": {
            "mean": None if not latencies else round(statistics.fmean(latencies), 6),
            "median": None if not latencies else round(statistics.median(latencies), 6),
            "p95": _percentile(latencies, 0.95),
            "maximum": None if not latencies else round(max(latencies), 6),
        },
        "reliability": {
            "exception_count": sum(item.exception is not None for item in turns),
            "warning_turn_count": sum(bool(item.warnings) for item in turns),
            "fallback_count": sum(item.fallback_used for item in turns),
        },
        "reported_token_usage": {
            "prompt_tokens": sum(item.prompt_tokens for item in turns),
            "completion_tokens": sum(item.completion_tokens for item in turns),
            "total_tokens": sum(item.prompt_tokens + item.completion_tokens for item in turns),
        },
        "recommendation_count_distribution": dict(sorted(recommendation_counts.items())),
        "ask_attribute_distribution": dict(sorted(question_counts.items())),
    }


def _git_metadata() -> dict:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        )
        return {"git_commit": commit, "git_dirty": dirty}
    except (OSError, subprocess.CalledProcessError):
        return {"git_commit": None, "git_dirty": None}


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, values: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for value in values:
            handle.write(json.dumps(value, sort_keys=True) + "\n")


def write_artifacts(
    config: BenchmarkConfig,
    experiment_id: str,
    created_at: datetime,
    samples: list[dict],
    sessions: list[SessionRecord],
    turns: list[TurnRecord],
    summary: dict,
) -> Path:
    """Write one self-contained benchmark run directory."""
    run_directory = Path(config.output_root) / experiment_id
    run_directory.mkdir(parents=True, exist_ok=False)

    serialized_config = asdict(config)
    config_hash = hashlib.sha256(
        json.dumps(serialized_config, sort_keys=True).encode("utf-8")
    ).hexdigest()
    manifest = {
        "experiment_id": experiment_id,
        "experiment_name": config.experiment_name,
        "created_at": created_at.isoformat(),
        "python_version": platform.python_version(),
        "catalog_path": config.catalog_path,
        "dataset_path": config.dataset_path,
        "split": "sample" if config.sample_id else config.split,
        "sample_id": config.sample_id,
        "seed": config.seed,
        "agent_variant": config.agent_variant,
        "retrieval_variant": config.retrieval_variant,
        "dense_variant": config.dense_variant,
        "reranker_variant": config.reranker_variant,
        "reranker_depth": config.reranker_depth,
        "reranker_batch_size": config.reranker_batch_size,
        "reranker_semantic_weight": config.reranker_semantic_weight,
        "orchestration_variant": config.orchestration_variant,
        "selected_sample_count": len(samples),
        "config_hash": config_hash,
        **_git_metadata(),
    }
    failures = [
        {
            "session": asdict(session),
            "problem_turns": [
                asdict(turn)
                for turn in turns
                if turn.sample_id == session.sample_id and (turn.exception or turn.warnings)
            ],
        }
        for session in sessions
        if not session.hit
        or any(
            turn.exception or turn.warnings
            for turn in turns
            if turn.sample_id == session.sample_id
        )
    ]

    _write_json(run_directory / "manifest.json", manifest)
    _write_json(run_directory / "config.json", serialized_config)
    _write_json(run_directory / "summary.json", summary)
    _write_json(
        run_directory / "split.json",
        {"sample_ids": [str(item["sample_id"]) for item in samples]},
    )
    _write_jsonl(run_directory / "sessions.jsonl", [asdict(item) for item in sessions])
    _write_jsonl(run_directory / "turns.jsonl", [asdict(item) for item in turns])
    _write_jsonl(run_directory / "failures.jsonl", failures)
    return run_directory
