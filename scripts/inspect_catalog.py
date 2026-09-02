from __future__ import annotations

import argparse
import json
import time
from collections import Counter

from starter.catalog import FACET_VERSION, SCHEMA_VERSION, Catalog, load_source_catalog
from starter.catalog_cache import get_cache_status, load_cached_catalog


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect normalized catalog coverage.")
    parser.add_argument("--catalog", default="data/catalog.jsonl")
    parser.add_argument("--cache-dir", default="data/cache")
    parser.add_argument(
        "--source-only",
        action="store_true",
        help="Ignore a valid cache and normalize the source catalog.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    return parser.parse_args()


def _coverage(catalog: Catalog) -> dict[str, dict[str, float | int]]:
    checks = {
        "title": lambda product: bool(product.title),
        "categories": lambda product: bool(product.categories),
        "features": lambda product: bool(product.features),
        "description": lambda product: bool(product.description),
        "details": lambda product: bool(product.details),
        "brand": lambda product: bool(product.brand),
        "price": lambda product: product.price is not None,
        "materials": lambda product: bool(product.materials),
        "colors": lambda product: bool(product.colors),
    }
    total = len(catalog)
    result: dict[str, dict[str, float | int]] = {}
    for field, check in checks.items():
        count = sum(check(product) for product in catalog.products)
        result[field] = {
            "count": count,
            "percent": round(100.0 * count / total, 2) if total else 0.0,
        }
    return result


def build_report(
    catalog: Catalog,
    *,
    cache_valid: bool,
    cache_reason: str,
    load_mode: str,
    load_seconds: float,
) -> dict[str, object]:
    material_counts = Counter(
        material for product in catalog.products for material in product.materials
    )
    color_counts = Counter(color for product in catalog.products for color in product.colors)
    paths = catalog.ontology.paths
    return {
        "schema_version": SCHEMA_VERSION,
        "facet_version": FACET_VERSION,
        "load_mode": load_mode,
        "load_seconds": round(load_seconds, 3),
        "cache": {"valid": cache_valid, "reason": cache_reason},
        "product_count": len(catalog),
        "unique_product_count": len(catalog.by_id),
        "field_coverage": _coverage(catalog),
        "facets": {
            "top_materials": material_counts.most_common(10),
            "top_colors": color_counts.most_common(10),
        },
        "categories": {
            "path_count": max(0, len(paths) - 1),
            "root_category_count": len(catalog.ontology.children()),
            "max_depth": max((len(path) for path in paths), default=0),
        },
    }


def _print_human(report: dict[str, object]) -> None:
    cache = report["cache"]
    categories = report["categories"]
    facets = report["facets"]
    print(f"Products: {report['product_count']:,} ({report['unique_product_count']:,} unique)")
    print(
        f"Schema: {report['schema_version']} | Facets: {report['facet_version']} | "
        f"Load: {report['load_mode']} in {report['load_seconds']:.3f}s"
    )
    print(f"Cache: {cache['reason']} (valid={cache['valid']})")
    print(
        f"Categories: {categories['path_count']:,} paths, "
        f"{categories['root_category_count']} roots, max depth {categories['max_depth']}"
    )
    print("Field coverage:")
    for field, values in report["field_coverage"].items():
        print(f"  {field:12} {values['count']:>6,}  {values['percent']:>6.2f}%")
    print(f"Top materials: {facets['top_materials']}")
    print(f"Top colors: {facets['top_colors']}")


def main() -> None:
    args = parse_args()
    status = get_cache_status(args.catalog, args.cache_dir)
    started = time.perf_counter()
    if status.valid and not args.source_only:
        catalog = load_cached_catalog(args.catalog, args.cache_dir, validate=False)
        load_mode = "cache"
    else:
        catalog = load_source_catalog(args.catalog)
        load_mode = "source"
    load_seconds = time.perf_counter() - started

    report = build_report(
        catalog,
        cache_valid=status.valid,
        cache_reason=status.reason,
        load_mode=load_mode,
        load_seconds=load_seconds,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        _print_human(report)


if __name__ == "__main__":
    main()
