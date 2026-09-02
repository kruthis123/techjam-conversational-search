from __future__ import annotations

import argparse
import json
from importlib.metadata import version
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

from starter.catalog_cache import load_catalog, sha256_file
from starter.dense import (
    DEFAULT_MODEL_DIRECTORY,
    DEFAULT_MODEL_ID,
    FIELDED_CACHE_ROOT,
    FieldedDenseDocumentCompiler,
    load_embedding_cache as _load_existing_cache,
    write_embedding_cache,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build deterministic field-aware embeddings from a local model."
    )
    parser.add_argument("--catalog", default="data/catalog.jsonl")
    parser.add_argument("--catalog-cache", default="data/cache")
    parser.add_argument("--embedding-root", default=FIELDED_CACHE_ROOT)
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--model-directory", default=DEFAULT_MODEL_DIRECTORY)
    parser.add_argument("--source-cache", default="data/cache/embeddings/bge-small-en-v1.5")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--batch-size", type=int, default=128)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.batch_size <= 0:
        raise SystemExit("--batch-size must be positive")
    model_directory = Path(args.model_directory)
    if not model_directory.is_dir():
        raise SystemExit(f"Local model is missing: {model_directory}")

    catalog = load_catalog(args.catalog, args.catalog_cache)
    asins = tuple(product.parent_asin for product in catalog.products)
    catalog_sha256 = sha256_file(args.catalog)
    _, source_manifest = _load_existing_cache(
        args.source_cache,
        expected_asins=asins,
        catalog_sha256=catalog_sha256,
        model_id=args.model_id,
    )
    model = SentenceTransformer(
        str(model_directory),
        device=args.device,
        local_files_only=True,
    )
    compiler = FieldedDenseDocumentCompiler()
    manifests: dict[str, dict[str, object]] = {}
    for view in ("identity", "attributes", "needs"):
        documents = [compiler.compile(product, view) for product in catalog.products]
        print(f"Encoding {len(documents):,} {view} views")
        matrix = model.encode(
            documents,
            batch_size=args.batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=True,
        )
        matrix = np.asarray(matrix, dtype=np.float32)
        manifest = write_embedding_cache(
            Path(args.embedding_root) / view,
            matrix,
            asins,
            {
                "catalog_sha256": catalog_sha256,
                "model_id": args.model_id,
                "model_revision": source_manifest.model_revision,
                "document_version": FieldedDenseDocumentCompiler.VERSIONS[view],
                "device": args.device,
                "max_sequence_length": model.max_seq_length,
                "license": source_manifest.license,
                "library_versions": {
                    "numpy": np.__version__,
                    "torch": version("torch"),
                    "transformers": version("transformers"),
                    "sentence_transformers": version("sentence-transformers"),
                },
            },
        )
        manifests[view] = manifest.to_dict()
    print(json.dumps(manifests, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
