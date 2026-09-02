from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from starter.catalog import (
    FACET_VERSION,
    SCHEMA_VERSION,
    Catalog,
    CategoryOntology,
    Product,
    catalog_from_products,
    load_source_catalog,
)


NORMALIZED_CATALOG_FILE = f"catalog_v{SCHEMA_VERSION}.jsonl"
ONTOLOGY_FILE = f"category_ontology_v{SCHEMA_VERSION}.json"
MANIFEST_FILE = f"catalog_manifest_v{SCHEMA_VERSION}.json"


@dataclass(frozen=True)
class CachePaths:
    directory: Path
    products: Path
    ontology: Path
    manifest: Path


@dataclass(frozen=True)
class CacheStatus:
    valid: bool
    reason: str
    manifest: Mapping[str, object] | None = None


def cache_paths(directory: str | Path) -> CachePaths:
    root = Path(directory)
    return CachePaths(
        directory=root,
        products=root / NORMALIZED_CATALOG_FILE,
        ontology=root / ONTOLOGY_FILE,
        manifest=root / MANIFEST_FILE,
    )


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def get_cache_status(source_path: str | Path, directory: str | Path) -> CacheStatus:
    source = Path(source_path)
    paths = cache_paths(directory)
    if not paths.manifest.exists():
        return CacheStatus(False, "manifest_missing")

    try:
        manifest = json.loads(paths.manifest.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return CacheStatus(False, "manifest_invalid")

    if manifest.get("schema_version") != SCHEMA_VERSION:
        return CacheStatus(False, "schema_version_changed", manifest)
    if manifest.get("facet_version") != FACET_VERSION:
        return CacheStatus(False, "facet_version_changed", manifest)
    if not paths.products.exists() or not paths.ontology.exists():
        return CacheStatus(False, "cache_file_missing", manifest)
    if not source.exists():
        return CacheStatus(False, "source_missing", manifest)
    if manifest.get("source_size") != source.stat().st_size:
        return CacheStatus(False, "source_size_changed", manifest)
    if manifest.get("source_sha256") != sha256_file(source):
        return CacheStatus(False, "source_checksum_changed", manifest)
    return CacheStatus(True, "valid", manifest)


def _write_products(path: Path, catalog: Catalog) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for product in catalog.products:
            handle.write(json.dumps(product.to_dict(), ensure_ascii=False, separators=(",", ":")))
            handle.write("\n")
    temporary.replace(path)


def _write_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )
    temporary.replace(path)


def build_catalog_cache(
    source_path: str | Path,
    directory: str | Path,
) -> tuple[Catalog, CachePaths, dict[str, object]]:
    source = Path(source_path)
    paths = cache_paths(directory)
    paths.directory.mkdir(parents=True, exist_ok=True)

    catalog = load_source_catalog(source)
    _write_products(paths.products, catalog)
    _write_json(paths.ontology, catalog.ontology.to_dict())

    manifest: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "facet_version": FACET_VERSION,
        "source_name": source.name,
        "source_size": source.stat().st_size,
        "source_sha256": sha256_file(source),
        "product_count": len(catalog),
        "normalized_catalog_file": paths.products.name,
        "ontology_file": paths.ontology.name,
    }
    _write_json(paths.manifest, manifest)
    return catalog, paths, manifest


def load_cached_catalog(
    source_path: str | Path,
    directory: str | Path,
    *,
    validate: bool = True,
) -> Catalog:
    paths = cache_paths(directory)
    if validate:
        status = get_cache_status(source_path, directory)
        if not status.valid:
            raise ValueError(f"catalog cache is not valid: {status.reason}")

    products: list[Product] = []
    with paths.products.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                products.append(Product.from_dict(json.loads(line)))
            except (json.JSONDecodeError, TypeError, ValueError) as error:
                raise ValueError(
                    f"invalid cached product at line {line_number}: {error}"
                ) from error

    ontology_value = json.loads(paths.ontology.read_text(encoding="utf-8"))
    ontology = CategoryOntology.from_dict(ontology_value)
    catalog = catalog_from_products(products, ontology)

    manifest = json.loads(paths.manifest.read_text(encoding="utf-8"))
    if manifest.get("product_count") != len(catalog):
        raise ValueError("cached product count does not match manifest")
    if ontology.product_ids(()) != tuple(product.parent_asin for product in products):
        raise ValueError("cached ontology root membership does not match products")
    return catalog


def load_catalog(
    source_path: str | Path,
    cache_directory: str | Path | None = None,
) -> Catalog:
    """Load a valid cache when supplied; otherwise normalize the source in memory."""
    if cache_directory is not None:
        status = get_cache_status(source_path, cache_directory)
        if status.valid:
            return load_cached_catalog(source_path, cache_directory, validate=False)
    return load_source_catalog(source_path)
