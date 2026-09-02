from __future__ import annotations

import argparse
import json
import time

from starter.catalog_cache import build_catalog_cache, get_cache_status


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the normalized catalog cache.")
    parser.add_argument("--catalog", default="data/catalog.jsonl")
    parser.add_argument("--cache-dir", default="data/cache")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild even when the existing cache is valid.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    status = get_cache_status(args.catalog, args.cache_dir)
    if status.valid and not args.force:
        print("Catalog cache is already valid; nothing was rebuilt.")
        print(json.dumps(dict(status.manifest or {}), indent=2, sort_keys=True))
        return

    started = time.perf_counter()
    catalog, paths, manifest = build_catalog_cache(args.catalog, args.cache_dir)
    elapsed = time.perf_counter() - started
    print(f"Built catalog cache for {len(catalog):,} products in {elapsed:.2f}s.")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    print(f"Products: {paths.products}")
    print(f"Ontology: {paths.ontology}")
    print(f"Manifest: {paths.manifest}")


if __name__ == "__main__":
    main()
