from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Mapping, Protocol, Sequence

from starter.catalog import Product
from starter.catalog_cache import sha256_file
from starter.retrieval import CandidateEvidence, RetrievalResult
from starter.state import StateView


RERANKER_NAMES = (
    "rerank_off",
    "minilm_l4_semantic",
    "minilm_l4_blended",
    "minilm_l4_fielded",
    "minilm_l4_constraint",
    "minilm_l4_guarded",
    "minilm_l4_route_aware",
    "minilm_l4_constraint_legacy",
    "minilm_l4_bounded",
    "minilm_l6_blended",
)
RERANK_QUERY_VERSION = "1"
RERANK_DOCUMENT_VERSION = "1"
RERANK_MANIFEST_FILE = "reranker_manifest.json"

L4_MODEL_ID = "cross-encoder/ms-marco-MiniLM-L4-v2"
L6_MODEL_ID = "cross-encoder/ms-marco-MiniLM-L6-v2"
L4_MODEL_DIRECTORY = "models/cross-encoder-ms-marco-MiniLM-L4-v2"
L6_MODEL_DIRECTORY = "models/cross-encoder-ms-marco-MiniLM-L6-v2"


class PairScorer(Protocol):
    def score(
        self,
        pairs: Sequence[tuple[str, str]],
        *,
        batch_size: int,
    ) -> Sequence[float]:
        """Return one relevance score for every query-document pair."""


@dataclass(frozen=True)
class RerankerConfig:
    name: str
    model_id: str = ""
    model_directory: str = ""
    depth: int = 60
    batch_size: int = 32
    rrf_k: int = 60
    retrieval_weight: float = 1.0
    semantic_weight: float = 0.25
    compatibility_weight: float = 0.0
    hard_contradiction_penalty: float = 0.0
    context_mode: str = "legacy"
    max_rank_movement: int | None = None


def reranker_config(
    name: str,
    *,
    depth: int | None = None,
    batch_size: int | None = None,
    semantic_weight: float | None = None,
) -> RerankerConfig:
    normalized = name.strip().casefold()
    if normalized not in RERANKER_NAMES:
        raise ValueError(f"reranker name must be one of {RERANKER_NAMES}")
    if normalized == "rerank_off":
        config = RerankerConfig(name=normalized, depth=0)
    else:
        is_l6 = normalized == "minilm_l6_blended"
        uses_fielded_context = normalized in {
            "minilm_l4_fielded",
            "minilm_l4_constraint",
            "minilm_l4_guarded",
        }
        uses_constraints = normalized in {
            "minilm_l4_constraint",
            "minilm_l4_guarded",
            "minilm_l4_constraint_legacy",
        }
        config = RerankerConfig(
            name=normalized,
            model_id=L6_MODEL_ID if is_l6 else L4_MODEL_ID,
            model_directory=L6_MODEL_DIRECTORY if is_l6 else L4_MODEL_DIRECTORY,
            retrieval_weight=0.0 if normalized.endswith("semantic") else 1.0,
            compatibility_weight=0.0015 if uses_constraints else 0.0,
            hard_contradiction_penalty=0.002 if uses_constraints else 0.0,
            context_mode=_context_mode(normalized, uses_fielded_context),
            max_rank_movement=(
                8
                if normalized in {"minilm_l4_guarded", "minilm_l4_bounded"}
                else None
            ),
        )
    if depth is not None:
        if depth <= 0:
            raise ValueError("rerank depth must be positive")
        config = replace(config, depth=depth)
    if batch_size is not None:
        if batch_size <= 0:
            raise ValueError("rerank batch size must be positive")
        config = replace(config, batch_size=batch_size)
    if semantic_weight is not None:
        if semantic_weight < 0:
            raise ValueError("semantic weight must not be negative")
        config = replace(config, semantic_weight=semantic_weight)
    return config


def _context_mode(name: str, uses_fielded_context: bool) -> str:
    if name == "minilm_l4_route_aware":
        return "route_aware"
    return "fielded" if uses_fielded_context else "legacy"


@dataclass(frozen=True)
class RerankerManifest:
    model_id: str
    model_revision: str
    license: str
    max_length: int
    device: str
    weight_file: str
    weight_sha256: str
    library_versions: Mapping[str, str]

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> RerankerManifest:
        try:
            versions = value["library_versions"]
            if not isinstance(versions, dict):
                raise TypeError("library_versions must be an object")
            return cls(
                model_id=str(value["model_id"]),
                model_revision=str(value["model_revision"]),
                license=str(value["license"]),
                max_length=int(value["max_length"]),
                device=str(value["device"]),
                weight_file=str(value["weight_file"]),
                weight_sha256=str(value["weight_sha256"]),
                library_versions={str(k): str(v) for k, v in versions.items()},
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"invalid reranker manifest: {error}") from error


@dataclass(frozen=True)
class RerankQuery:
    text: str
    version: str = RERANK_QUERY_VERSION


@dataclass(frozen=True)
class RerankCandidate:
    parent_asin: str
    original_rank: int
    semantic_rank: int
    semantic_score: float
    retrieval_contribution: float
    semantic_contribution: float
    compatibility_contribution: float
    contradiction_penalty: float
    final_score: float


@dataclass(frozen=True)
class RerankResult:
    retrieval_result: RetrievalResult
    query: RerankQuery
    candidates: tuple[RerankCandidate, ...]
    model_id: str
    model_revision: str
    context_mode: str
    depth: int
    batch_size: int
    inference_latency_ms: float

    @property
    def candidate_ids(self) -> tuple[str, ...]:
        return self.retrieval_result.candidate_ids


class RerankQueryCompiler:
    SLOT_ORDER = (
        "category",
        "audience",
        "brand",
        "material",
        "color",
        "size",
        "style",
        "use_case",
        "feature",
        "min_price",
        "max_price",
        "target_price",
    )

    def compile(
        self,
        user_message: str,
        state: StateView,
        mode: str = "legacy",
    ) -> RerankQuery:
        if mode == "fielded":
            return self._compile_fielded(user_message, state)
        if mode != "legacy":
            raise ValueError(f"unknown rerank query mode: {mode}")
        parts = ["Shopping request."]
        for name in self._slot_names(state):
            slot = state.active_slots[name]
            values = ", ".join(str(value.normalized_value) for value in slot.values)
            if values:
                parts.append(f"{name.replace('_', ' ').title()}: {values}.")
        message = user_message.strip()
        if message:
            parts.append(f"Current request: {message}")
        return RerankQuery(" ".join(parts))

    def _compile_fielded(self, user_message: str, state: StateView) -> RerankQuery:
        required: list[str] = []
        preferred: list[str] = []
        for name in self._slot_names(state):
            slot = state.active_slots[name]
            values = ", ".join(str(value.normalized_value) for value in slot.values)
            if not values:
                continue
            item = f"{name.replace('_', ' ')}: {values}"
            target = (
                required
                if any(value.strength == "hard" for value in slot.values)
                else preferred
            )
            target.append(item)
        parts = ["Find the best matching product."]
        if required:
            parts.append("Required: " + "; ".join(required) + ".")
        if preferred:
            parts.append("Preferred: " + "; ".join(preferred) + ".")
        if user_message.strip():
            parts.append("Current request: " + user_message.strip())
        return RerankQuery(" ".join(parts), version="2")

    def _slot_names(self, state: StateView) -> tuple[str, ...]:
        known = [name for name in self.SLOT_ORDER if name in state.active_slots]
        extras = sorted(set(state.active_slots) - set(self.SLOT_ORDER))
        return tuple(known + extras)


class RerankDocumentCompiler:
    def __init__(self, max_characters: int = 768) -> None:
        if max_characters <= 0:
            raise ValueError("max_characters must be positive")
        self.max_characters = max_characters

    def compile(self, product: Product, mode: str = "legacy") -> str:
        if mode == "legacy":
            return product.dense_text[: self.max_characters].strip()
        if mode != "fielded":
            raise ValueError(f"unknown rerank document mode: {mode}")
        parts = (
            f"Product: {product.title}." if product.title else "",
            f"Category: {product.categories_text}." if product.categories else "",
            f"Brand: {product.brand}." if product.brand else "",
            f"Materials: {', '.join(product.materials)}." if product.materials else "",
            f"Colors: {', '.join(product.colors)}." if product.colors else "",
            f"Price: {product.price:.2f}." if product.price is not None else "",
            f"Features: {product.features_text}." if product.features else "",
            f"Details: {product.details_text}." if product.details else "",
            f"Description: {product.description_text}." if product.description else "",
        )
        return " ".join(part for part in parts if part)[: self.max_characters].strip()


def load_reranker_manifest(
    model_directory: str | Path,
    expected_model_id: str,
) -> RerankerManifest:
    root = Path(model_directory)
    manifest_path = root / RERANK_MANIFEST_FILE
    if not manifest_path.is_file():
        raise FileNotFoundError(f"reranker manifest is missing: {manifest_path}")
    try:
        value = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        raise ValueError("reranker manifest is invalid") from error
    if not isinstance(value, dict):
        raise ValueError("reranker manifest must be an object")
    manifest = RerankerManifest.from_dict(value)
    if manifest.model_id != expected_model_id:
        raise ValueError("reranker model ID does not match configuration")
    weight_path = root / manifest.weight_file
    if not weight_path.is_file():
        raise FileNotFoundError(f"reranker weight file is missing: {weight_path}")
    if sha256_file(weight_path) != manifest.weight_sha256:
        raise ValueError("reranker weight checksum does not match manifest")
    return manifest


class CrossEncoderScorer:
    """Sentence Transformers adapter that only loads a prepared local model."""

    def __init__(self, model_directory: str | Path, device: str = "cpu") -> None:
        root = Path(model_directory)
        if not root.is_dir():
            raise FileNotFoundError(f"local reranker model is missing: {root}")
        try:
            from sentence_transformers import CrossEncoder
        except ImportError as error:
            raise RuntimeError("sentence-transformers is not installed") from error
        self.model = CrossEncoder(
            str(root),
            device=device,
            local_files_only=True,
        )

    def score(
        self,
        pairs: Sequence[tuple[str, str]],
        *,
        batch_size: int,
    ) -> Sequence[float]:
        values = self.model.predict(
            list(pairs),
            batch_size=batch_size,
            show_progress_bar=False,
        )
        if hasattr(values, "reshape"):
            values = values.reshape(-1)
        return tuple(float(value) for value in values)


class SemanticReranker:
    def __init__(
        self,
        products: Sequence[Product],
        config: RerankerConfig,
        scorer: PairScorer,
        manifest: RerankerManifest,
    ) -> None:
        self.config = config
        self.scorer = scorer
        self.manifest = manifest
        compiler = RerankDocumentCompiler()
        document_modes = {"legacy"}
        if config.context_mode in {"fielded", "route_aware"}:
            document_modes.add("fielded")
        self.documents = {
            mode: {
                product.parent_asin: compiler.compile(product, mode)
                for product in products
            }
            for mode in document_modes
        }
        self.query_compiler = RerankQueryCompiler()

    def rerank(
        self,
        user_message: str,
        state: StateView,
        retrieval_result: RetrievalResult,
        config: RerankerConfig | None = None,
        route: str = "buying",
    ) -> RerankResult:
        selected = config or self.config
        if selected.name == "rerank_off":
            raise ValueError("rerank_off cannot execute semantic reranking")
        if selected.model_id != self.config.model_id:
            raise ValueError("per-call reranker config must use the loaded model")
        context_mode = selected.context_mode
        if context_mode == "route_aware":
            context_route = state.initial_route or route
            context_mode = "fielded" if context_route == "browsing" else "legacy"
        query = self.query_compiler.compile(
            user_message,
            state,
            mode=context_mode,
        )
        depth = min(selected.depth, len(retrieval_result.candidates))
        if depth == 0:
            return RerankResult(
                retrieval_result=retrieval_result,
                query=query,
                candidates=(),
                model_id=self.manifest.model_id,
                model_revision=self.manifest.model_revision,
                context_mode=context_mode,
                depth=0,
                batch_size=selected.batch_size,
                inference_latency_ms=0.0,
            )

        head = retrieval_result.candidates[:depth]
        documents = self.documents[context_mode]
        pairs = [(query.text, documents[item.parent_asin]) for item in head]
        started = time.perf_counter_ns()
        raw_scores = self.scorer.score(pairs, batch_size=selected.batch_size)
        latency_ms = (time.perf_counter_ns() - started) / 1_000_000
        scores = tuple(float(value) for value in raw_scores)
        if len(scores) != depth:
            raise ValueError("reranker returned the wrong number of scores")
        if not all(math.isfinite(value) for value in scores):
            raise ValueError("reranker returned a non-finite score")

        semantic_order = sorted(range(depth), key=lambda index: (-scores[index], index))
        semantic_ranks = {
            index: rank for rank, index in enumerate(semantic_order, start=1)
        }
        details: list[RerankCandidate] = []
        by_id: dict[str, RerankCandidate] = {}
        hard_slots = {
            name
            for name, slot in state.active_slots.items()
            if any(value.strength == "hard" for value in slot.values)
        }
        for index, candidate in enumerate(head):
            original_rank = index + 1
            semantic_rank = semantic_ranks[index]
            retrieval_contribution = selected.retrieval_weight / (
                selected.rrf_k + original_rank
            )
            semantic_contribution = selected.semantic_weight / (
                selected.rrf_k + semantic_rank
            )
            compatibility_contribution = (
                selected.compatibility_weight
                * math.tanh(candidate.compatibility_score / 3.0)
            )
            contradiction_count = len(
                hard_slots & set(candidate.contradicted_constraints)
            )
            contradiction_penalty = (
                selected.hard_contradiction_penalty * contradiction_count
            )
            detail = RerankCandidate(
                parent_asin=candidate.parent_asin,
                original_rank=original_rank,
                semantic_rank=semantic_rank,
                semantic_score=scores[index],
                retrieval_contribution=round(retrieval_contribution, 8),
                semantic_contribution=round(semantic_contribution, 8),
                compatibility_contribution=round(compatibility_contribution, 8),
                contradiction_penalty=round(contradiction_penalty, 8),
                final_score=round(
                    retrieval_contribution
                    + semantic_contribution
                    + compatibility_contribution
                    - contradiction_penalty,
                    8,
                ),
            )
            details.append(detail)
            by_id[detail.parent_asin] = detail

        ranked_head = self._rank_head(
            head,
            by_id,
            selected.max_rank_movement,
        )
        reranked_head = tuple(
            replace(candidate, fused_score=by_id[candidate.parent_asin].final_score)
            for candidate in ranked_head
        )
        result = RetrievalResult(
            candidates=reranked_head + retrieval_result.candidates[depth:],
            routes=retrieval_result.routes,
            queries=retrieval_result.queries,
            config_name=retrieval_result.config_name,
            warnings=retrieval_result.warnings,
        )
        ranked_details = tuple(by_id[item.parent_asin] for item in ranked_head)
        return RerankResult(
            retrieval_result=result,
            query=query,
            candidates=ranked_details,
            model_id=self.manifest.model_id,
            model_revision=self.manifest.model_revision,
            context_mode=context_mode,
            depth=depth,
            batch_size=selected.batch_size,
            inference_latency_ms=round(latency_ms, 6),
        )

    def _rank_head(
        self,
        head: Sequence[CandidateEvidence],
        by_id: Mapping[str, RerankCandidate],
        max_rank_movement: int | None,
    ) -> list[CandidateEvidence]:
        def key(candidate: CandidateEvidence) -> tuple[float, int, str]:
            detail = by_id[candidate.parent_asin]
            return (-detail.final_score, detail.original_rank, candidate.parent_asin)

        if max_rank_movement is None:
            return sorted(head, key=key)

        ranked = list(head)
        for _ in range(len(ranked)):
            changed = False
            for index in range(len(ranked) - 1):
                left = ranked[index]
                right = ranked[index + 1]
                if key(right) >= key(left):
                    continue
                left_original = by_id[left.parent_asin].original_rank
                right_original = by_id[right.parent_asin].original_rank
                if (
                    abs((index + 2) - left_original) > max_rank_movement
                    or abs((index + 1) - right_original) > max_rank_movement
                ):
                    continue
                ranked[index], ranked[index + 1] = right, left
                changed = True
            if not changed:
                break
        return ranked
