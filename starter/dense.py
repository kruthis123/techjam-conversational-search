from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping, Protocol, Sequence

from starter.catalog import Product
from starter.catalog_cache import sha256_file
from starter.state import StateView


DENSE_NAMES = (
    "dense_off",
    "dense_only",
    "hybrid_dense",
    "hybrid_dense_multi",
    "hybrid_dense_rescue",
    "hybrid_dense_profile",
    "hybrid_dense_v2",
    "hybrid_dense_fielded",
    "hybrid_dense_fielded_profile",
)
DENSE_SCHEMA_VERSION = "1"
DOCUMENT_VERSION = "3"
QUERY_VERSION = "1"
DEFAULT_MODEL_ID = "BAAI/bge-small-en-v1.5"
DEFAULT_MODEL_DIRECTORY = "models/BAAI_bge-small-en-v1.5"
DEFAULT_CACHE_DIRECTORY = "data/cache/embeddings/bge-small-en-v1.5"
FIELDED_CACHE_ROOT = "data/cache/embeddings/bge-small-en-v1.5-fielded"
QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "


class TextEncoder(Protocol):
    def encode(
        self,
        texts: Sequence[str],
        *,
        batch_size: int,
        normalize_embeddings: bool,
    ) -> object:
        """Encode text into a two-dimensional numeric array."""


@dataclass(frozen=True)
class DenseConfig:
    name: str
    model_id: str = DEFAULT_MODEL_ID
    model_directory: str = DEFAULT_MODEL_DIRECTORY
    cache_directory: str = DEFAULT_CACHE_DIRECTORY
    depth: int = 400
    batch_size: int = 128
    rrf_k: int = 60
    query_mode: str = "single"
    fusion_mode: str = "rrf"
    rescue_depth: int = 20
    view_cache_directories: tuple[tuple[str, str], ...] = ()


def dense_config(name: str) -> DenseConfig:
    normalized = name.strip().casefold()
    if normalized not in DENSE_NAMES:
        raise ValueError(f"dense name must be one of {DENSE_NAMES}")
    if normalized == "hybrid_dense_multi":
        return DenseConfig(name=normalized, query_mode="multi")
    if normalized == "hybrid_dense_rescue":
        return DenseConfig(name=normalized, fusion_mode="rescue")
    if normalized == "hybrid_dense_profile":
        return DenseConfig(name=normalized, query_mode="multi_profile")
    if normalized == "hybrid_dense_v2":
        return DenseConfig(
            name=normalized,
            query_mode="multi_profile",
            fusion_mode="rescue",
        )
    if normalized in {"hybrid_dense_fielded", "hybrid_dense_fielded_profile"}:
        return DenseConfig(
            name=normalized,
            query_mode=(
                "multi_profile"
                if normalized.endswith("profile")
                else "multi"
            ),
            fusion_mode="rescue",
            view_cache_directories=tuple(
                (name, f"{FIELDED_CACHE_ROOT}/{name}")
                for name in ("identity", "attributes", "needs")
            ),
        )
    return DenseConfig(name=normalized)


@dataclass(frozen=True)
class EmbeddingManifest:
    schema_version: str
    catalog_sha256: str
    product_count: int
    model_id: str
    model_revision: str
    document_version: str
    query_version: str
    dimension: int
    dtype: str
    normalized: bool
    embeddings_sha256: str
    asins_sha256: str
    device: str
    max_sequence_length: int
    license: str
    library_versions: Mapping[str, str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> EmbeddingManifest:
        try:
            versions = value["library_versions"]
            if not isinstance(versions, dict):
                raise TypeError("library_versions must be an object")
            return cls(
                schema_version=str(value["schema_version"]),
                catalog_sha256=str(value["catalog_sha256"]),
                product_count=int(value["product_count"]),
                model_id=str(value["model_id"]),
                model_revision=str(value["model_revision"]),
                document_version=str(value["document_version"]),
                query_version=str(value["query_version"]),
                dimension=int(value["dimension"]),
                dtype=str(value["dtype"]),
                normalized=bool(value["normalized"]),
                embeddings_sha256=str(value["embeddings_sha256"]),
                asins_sha256=str(value["asins_sha256"]),
                device=str(value["device"]),
                max_sequence_length=int(value["max_sequence_length"]),
                license=str(value["license"]),
                library_versions={str(k): str(v) for k, v in versions.items()},
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"invalid embedding manifest: {error}") from error


@dataclass(frozen=True)
class DenseQuery:
    text: str
    version: str = QUERY_VERSION
    name: str = "complete"


@dataclass(frozen=True)
class DenseRouteResult:
    name: str
    query: DenseQuery
    candidate_ids: tuple[str, ...]
    scores: tuple[float, ...]


@dataclass(frozen=True)
class DenseResult:
    query: DenseQuery
    candidate_ids: tuple[str, ...]
    scores: tuple[float, ...]
    model_id: str
    model_revision: str
    device: str
    encode_latency_ms: float
    cache_status: str = "valid"
    routes: tuple[DenseRouteResult, ...] = ()


@dataclass(frozen=True)
class DenseCachePaths:
    directory: Path
    embeddings: Path
    asins: Path
    manifest: Path


def dense_cache_paths(directory: str | Path) -> DenseCachePaths:
    root = Path(directory)
    return DenseCachePaths(
        directory=root,
        embeddings=root / "embeddings.npy",
        asins=root / "asins.json",
        manifest=root / "manifest.json",
    )


class DenseDocumentCompiler:
    def __init__(self, max_characters: int = 512) -> None:
        if max_characters <= 0:
            raise ValueError("max_characters must be positive")
        self.max_characters = max_characters

    def compile(self, product: Product) -> str:
        return product.dense_text[: self.max_characters].strip()


class FieldedDenseDocumentCompiler:
    """Create aligned product views for identity, constraints, and use cases."""

    VERSIONS = {
        "identity": "4-identity",
        "attributes": "4-attributes",
        "needs": "4-needs",
    }

    def __init__(self, max_characters: int = 512) -> None:
        if max_characters <= 0:
            raise ValueError("max_characters must be positive")
        self.max_characters = max_characters

    def compile(self, product: Product, view: str) -> str:
        if view == "identity":
            parts = (
                f"Product: {product.title}." if product.title else "",
                f"Category: {product.categories_text}." if product.categories else "",
                f"Brand: {product.brand}." if product.brand else "",
            )
        elif view == "attributes":
            parts = (
                f"Product type: {product.categories[-1]}." if product.categories else "",
                f"Materials: {', '.join(product.materials)}." if product.materials else "",
                f"Colors: {', '.join(product.colors)}." if product.colors else "",
                f"Price: {product.price:.2f}." if product.price is not None else "",
                f"Features: {product.features_text}." if product.features else "",
                f"Details: {product.details_text}." if product.details else "",
            )
        elif view == "needs":
            parts = (
                f"{product.categories[-1]} for shopping needs." if product.categories else "",
                f"Product: {product.title}." if product.title else "",
                f"Useful features: {product.features_text}." if product.features else "",
                f"Suitable for: {product.description_text}." if product.description else "",
            )
        else:
            raise ValueError(f"unknown dense document view: {view}")
        return " ".join(part for part in parts if part)[: self.max_characters].strip()


class DenseQueryCompiler:
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

    def compile(self, user_message: str, state: StateView) -> DenseQuery:
        lines = ["Shopping request."]
        for name in self._ordered_slot_names(state):
            slot = state.active_slots[name]
            values = ", ".join(str(value.normalized_value) for value in slot.values)
            if values:
                lines.append(f"{name.replace('_', ' ').title()}: {values}.")
        message = user_message.strip()
        if message:
            lines.append(f"Current request: {message}")
        return DenseQuery(QUERY_INSTRUCTION + "\n".join(lines))

    def compile_views(
        self,
        user_message: str,
        state: StateView,
        *,
        include_profile: bool,
    ) -> tuple[DenseQuery, ...]:
        views: list[DenseQuery] = []
        identity = self._slot_text(state, ("category", "audience", "brand"))
        if identity:
            views.append(self._query("identity", f"Product identity: {identity}."))

        constraints = self._slot_text(
            state,
            ("material", "color", "style", "use_case", "feature"),
        )
        if constraints:
            views.append(
                self._query("constraints", f"Product requirements: {constraints}.")
            )

        scenario_parts = [user_message.strip()]
        scenario_slots = self._slot_text(state, ("use_case", "feature", "style"))
        if scenario_slots:
            scenario_parts.append(scenario_slots)
        scenario = " ".join(part for part in scenario_parts if part)
        if scenario:
            views.append(self._query("scenario", f"Shopping scenario: {scenario}"))

        if include_profile:
            profile = self._profile_text(state)
            if profile:
                views.append(
                    self._query("profile", f"Soft customer preferences: {profile}")
                )
        return tuple(views) or (self.compile(user_message, state),)

    def _query(self, name: str, text: str) -> DenseQuery:
        return DenseQuery(QUERY_INSTRUCTION + text, name=name)

    def _slot_text(self, state: StateView, names: Sequence[str]) -> str:
        parts: list[str] = []
        for name in names:
            slot = state.active_slots.get(name)
            if slot is None:
                continue
            values = ", ".join(str(value.normalized_value) for value in slot.values)
            if values:
                parts.append(f"{name.replace('_', ' ')}: {values}")
        return "; ".join(parts)

    def _profile_text(self, state: StateView) -> str:
        parts: list[str] = []
        tags = state.user_profile.get("preference_tags")
        if isinstance(tags, list):
            values = [str(value).strip() for value in tags if str(value).strip()]
            if values:
                parts.append("preferences: " + ", ".join(values))
        summary = state.user_profile.get("summary")
        if isinstance(summary, str) and summary.strip():
            parts.append("history: " + summary.strip())
        return "; ".join(parts)

    def _ordered_slot_names(self, state: StateView) -> tuple[str, ...]:
        known = [name for name in self.SLOT_ORDER if name in state.active_slots]
        extras = sorted(set(state.active_slots) - set(self.SLOT_ORDER))
        return tuple(known + extras)


class SentenceTransformerEncoder:
    """Thin adapter that loads only a local Sentence Transformers model."""

    def __init__(self, model_directory: str | Path, device: str = "cpu") -> None:
        model_path = Path(model_directory)
        if not model_path.is_dir():
            raise FileNotFoundError(f"local dense model is missing: {model_path}")
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as error:
            raise RuntimeError("sentence-transformers is not installed") from error
        self.model = SentenceTransformer(
            str(model_path),
            device=device,
            local_files_only=True,
        )

    def encode(
        self,
        texts: Sequence[str],
        *,
        batch_size: int,
        normalize_embeddings: bool,
    ) -> object:
        return self.model.encode(
            list(texts),
            batch_size=batch_size,
            normalize_embeddings=normalize_embeddings,
            convert_to_numpy=True,
            show_progress_bar=False,
        )


class ExactDenseIndex:
    def __init__(self, asins: Sequence[str], matrix: object) -> None:
        np = _numpy()
        values = np.asarray(matrix, dtype=np.float32)
        if values.ndim != 2:
            raise ValueError("embedding matrix must have two dimensions")
        if values.shape[0] != len(asins):
            raise ValueError("embedding rows must match ASIN count")
        if not np.isfinite(values).all():
            raise ValueError("embedding matrix contains non-finite values")
        self.asins = tuple(asins)
        self.matrix = values

    @property
    def dimension(self) -> int:
        return int(self.matrix.shape[1])

    def search(self, query_vector: object, top_k: int) -> tuple[tuple[str, ...], tuple[float, ...]]:
        np = _numpy()
        vector = np.asarray(query_vector, dtype=np.float32).reshape(-1)
        if vector.shape[0] != self.dimension:
            raise ValueError("query dimension does not match embedding matrix")
        if not np.isfinite(vector).all():
            raise ValueError("query vector contains non-finite values")
        norm = float(np.linalg.norm(vector))
        if norm == 0.0:
            raise ValueError("query vector must not be zero")
        vector = vector / norm
        scores = self.matrix @ vector
        limit = min(max(top_k, 0), len(self.asins))
        if limit == 0:
            return (), ()

        if limit == len(self.asins):
            selected = np.arange(len(self.asins))
        else:
            rough = np.argpartition(-scores, limit - 1)[:limit]
            threshold = float(scores[rough].min())
            above = np.flatnonzero(scores > threshold)
            tied = np.flatnonzero(scores == threshold)[: limit - len(above)]
            selected = np.concatenate((above, tied))
        order = np.lexsort((selected, -scores[selected]))
        ranked = selected[order]
        return (
            tuple(self.asins[int(index)] for index in ranked),
            tuple(float(scores[int(index)]) for index in ranked),
        )


class DenseRetriever:
    def __init__(
        self,
        config: DenseConfig,
        encoder: TextEncoder,
        expected_asins: Sequence[str],
        catalog_sha256: str,
    ) -> None:
        self.config = config
        self.encoder = encoder
        self.indexes: dict[str, ExactDenseIndex] = {}
        if config.view_cache_directories:
            manifests: list[EmbeddingManifest] = []
            for view, directory in config.view_cache_directories:
                matrix, manifest = load_embedding_cache(
                    directory,
                    expected_asins=expected_asins,
                    catalog_sha256=catalog_sha256,
                    model_id=config.model_id,
                    expected_document_version=FieldedDenseDocumentCompiler.VERSIONS[view],
                )
                self.indexes[view] = ExactDenseIndex(expected_asins, matrix)
                manifests.append(manifest)
            self.manifest = manifests[0]
            self.index = self.indexes["identity"]
        else:
            matrix, manifest = load_embedding_cache(
                config.cache_directory,
                expected_asins=expected_asins,
                catalog_sha256=catalog_sha256,
                model_id=config.model_id,
            )
            self.manifest = manifest
            self.index = ExactDenseIndex(expected_asins, matrix)
            self.indexes["complete"] = self.index
        self.query_compiler = DenseQueryCompiler()

    def retrieve(
        self,
        user_message: str,
        state: StateView,
        route: str = "browsing",
    ) -> DenseResult:
        np = _numpy()
        if self.config.query_mode == "single":
            queries = (self.query_compiler.compile(user_message, state),)
        else:
            queries = self.query_compiler.compile_views(
                user_message,
                state,
                include_profile=self.config.query_mode == "multi_profile",
            )
        started = time.perf_counter_ns()
        encoded = self.encoder.encode(
            tuple(query.text for query in queries),
            batch_size=len(queries),
            normalize_embeddings=True,
        )
        encode_latency_ms = (time.perf_counter_ns() - started) / 1_000_000
        array = np.asarray(encoded, dtype=np.float32)
        if array.shape != (len(queries), self.index.dimension):
            raise ValueError("encoder returned an unexpected query shape")
        routes = tuple(
            DenseRouteResult(
                name=query.name,
                query=query,
                candidate_ids=candidate_ids,
                scores=scores,
            )
            for query, vector in zip(queries, array)
            for candidate_ids, scores in (
                self._index_for_query(query.name).search(vector, self.config.depth),
            )
        )
        candidate_ids, scores = self._fuse_routes(routes, route)
        return DenseResult(
            query=queries[0],
            candidate_ids=candidate_ids,
            scores=scores,
            model_id=self.manifest.model_id,
            model_revision=self.manifest.model_revision,
            device=self.manifest.device,
            encode_latency_ms=round(encode_latency_ms, 6),
            routes=routes,
        )

    def _index_for_query(self, query_name: str) -> ExactDenseIndex:
        if not self.config.view_cache_directories:
            return self.index
        view = {
            "identity": "identity",
            "constraints": "attributes",
            "scenario": "needs",
            "profile": "needs",
            "complete": "needs",
        }.get(query_name, "needs")
        return self.indexes[view]

    def _fuse_routes(
        self,
        routes: Sequence[DenseRouteResult],
        route: str,
    ) -> tuple[tuple[str, ...], tuple[float, ...]]:
        if len(routes) == 1:
            return routes[0].candidate_ids, routes[0].scores
        browsing = route == "browsing"
        weights = {
            "identity": 0.9 if browsing else 1.3,
            "constraints": 0.9 if browsing else 1.2,
            "scenario": 1.4 if browsing else 1.0,
            "profile": 0.3,
        }
        fused: dict[str, float] = {}
        best_rank: dict[str, int] = {}
        for route in routes:
            weight = weights.get(route.name, 1.0)
            for rank, parent_asin in enumerate(route.candidate_ids, start=1):
                fused[parent_asin] = fused.get(parent_asin, 0.0) + weight / (
                    self.config.rrf_k + rank
                )
                best_rank[parent_asin] = min(best_rank.get(parent_asin, rank), rank)
        ranked = sorted(
            fused,
            key=lambda parent_asin: (
                -fused[parent_asin],
                best_rank[parent_asin],
                parent_asin,
            ),
        )[: self.config.depth]
        return (
            tuple(ranked),
            tuple(round(fused[parent_asin], 8) for parent_asin in ranked),
        )


def load_embedding_cache(
    directory: str | Path,
    *,
    expected_asins: Sequence[str],
    catalog_sha256: str,
    model_id: str,
    expected_document_version: str = DOCUMENT_VERSION,
) -> tuple[object, EmbeddingManifest]:
    np = _numpy()
    paths = dense_cache_paths(directory)
    for path in (paths.embeddings, paths.asins, paths.manifest):
        if not path.is_file():
            raise FileNotFoundError(f"dense cache file is missing: {path}")

    try:
        manifest_value = json.loads(paths.manifest.read_text(encoding="utf-8"))
        asin_value = json.loads(paths.asins.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        raise ValueError("dense cache metadata is invalid") from error
    if not isinstance(manifest_value, dict) or not isinstance(asin_value, list):
        raise ValueError("dense cache metadata has the wrong shape")
    manifest = EmbeddingManifest.from_dict(manifest_value)
    asins = tuple(str(value) for value in asin_value)

    checks = {
        "schema version": manifest.schema_version == DENSE_SCHEMA_VERSION,
        "catalog checksum": manifest.catalog_sha256 == catalog_sha256,
        "product count": manifest.product_count == len(expected_asins),
        "ASIN order": asins == tuple(expected_asins),
        "model ID": manifest.model_id == model_id,
        "document version": manifest.document_version == expected_document_version,
        "query version": manifest.query_version == QUERY_VERSION,
        "normalization": manifest.normalized,
        "embedding checksum": manifest.embeddings_sha256 == sha256_file(paths.embeddings),
        "ASIN checksum": manifest.asins_sha256 == sha256_file(paths.asins),
    }
    failed = [name for name, valid in checks.items() if not valid]
    if failed:
        raise ValueError("dense cache mismatch: " + ", ".join(failed))

    matrix = np.load(paths.embeddings, allow_pickle=False)
    if matrix.dtype != np.float16:
        raise ValueError("dense cache matrix must use float16 on disk")
    if matrix.shape != (manifest.product_count, manifest.dimension):
        raise ValueError("dense cache matrix shape does not match manifest")
    matrix = np.asarray(matrix, dtype=np.float32)
    norms = np.linalg.norm(matrix, axis=1)
    if not np.allclose(norms, 1.0, atol=0.002):
        raise ValueError("dense cache matrix is not normalized")
    return matrix, manifest


def write_embedding_cache(
    directory: str | Path,
    matrix: object,
    asins: Sequence[str],
    manifest_fields: Mapping[str, object],
) -> EmbeddingManifest:
    np = _numpy()
    paths = dense_cache_paths(directory)
    paths.directory.mkdir(parents=True, exist_ok=True)
    values = np.asarray(matrix, dtype=np.float32)
    if values.ndim != 2 or values.shape[0] != len(asins):
        raise ValueError("embedding matrix and ASIN list are not aligned")
    norms = np.linalg.norm(values, axis=1)
    if not np.allclose(norms, 1.0, atol=0.001):
        raise ValueError("embeddings must be L2-normalized before writing")

    embedding_temp = paths.embeddings.with_suffix(".npy.tmp")
    asin_temp = paths.asins.with_suffix(".json.tmp")
    with embedding_temp.open("wb") as handle:
        np.save(handle, values.astype(np.float16), allow_pickle=False)
    asin_temp.write_text(
        json.dumps(list(asins), ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    embedding_temp.replace(paths.embeddings)
    asin_temp.replace(paths.asins)

    manifest = EmbeddingManifest(
        schema_version=DENSE_SCHEMA_VERSION,
        catalog_sha256=str(manifest_fields["catalog_sha256"]),
        product_count=len(asins),
        model_id=str(manifest_fields["model_id"]),
        model_revision=str(manifest_fields["model_revision"]),
        document_version=str(
            manifest_fields.get("document_version", DOCUMENT_VERSION)
        ),
        query_version=QUERY_VERSION,
        dimension=int(values.shape[1]),
        dtype="float16",
        normalized=True,
        embeddings_sha256=sha256_file(paths.embeddings),
        asins_sha256=sha256_file(paths.asins),
        device=str(manifest_fields["device"]),
        max_sequence_length=int(manifest_fields["max_sequence_length"]),
        license=str(manifest_fields["license"]),
        library_versions={
            str(key): str(value)
            for key, value in dict(manifest_fields["library_versions"]).items()
        },
    )
    manifest_temp = paths.manifest.with_suffix(".json.tmp")
    manifest_temp.write_text(
        json.dumps(manifest.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    manifest_temp.replace(paths.manifest)
    return manifest


def _numpy():
    try:
        import numpy as np
    except ImportError as error:
        raise RuntimeError("numpy is not installed") from error
    return np
