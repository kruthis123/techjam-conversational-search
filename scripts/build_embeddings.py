from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import sentence_transformers
import torch
import transformers
from huggingface_hub import HfApi
from sentence_transformers import SentenceTransformer

from starter.catalog_cache import load_catalog, sha256_file
from starter.dense import (
    DEFAULT_CACHE_DIRECTORY,
    DEFAULT_MODEL_DIRECTORY,
    DEFAULT_MODEL_ID,
    DenseDocumentCompiler,
    write_embedding_cache,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download a pinned encoder and precompute catalog embeddings."
    )
    parser.add_argument("--catalog", default="data/catalog.jsonl")
    parser.add_argument("--catalog-cache", default="data/cache")
    parser.add_argument("--embedding-cache", default=DEFAULT_CACHE_DIRECTORY)
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--model-directory", default=DEFAULT_MODEL_DIRECTORY)
    parser.add_argument("--revision", help="Optional Hugging Face model commit or tag.")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--batch-size", type=int, default=128)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.batch_size <= 0:
        raise SystemExit("--batch-size must be positive")

    info = HfApi().model_info(args.model_id, revision=args.revision)
    revision = str(info.sha)
    print(f"Loading {args.model_id} at revision {revision}")
    model = SentenceTransformer(
        args.model_id,
        revision=revision,
        device=args.device,
    )
    model_directory = Path(args.model_directory)
    model_directory.parent.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(model_directory))

    catalog = load_catalog(args.catalog, args.catalog_cache)
    compiler = DenseDocumentCompiler()
    documents = [compiler.compile(product) for product in catalog.products]
    asins = [product.parent_asin for product in catalog.products]
    print(f"Encoding {len(documents):,} products")
    matrix = model.encode(
        documents,
        batch_size=args.batch_size,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=True,
    )
    matrix = np.asarray(matrix, dtype=np.float32)

    card_data = getattr(info, "card_data", None)
    license_name = getattr(card_data, "license", None) or "unknown"
    manifest = write_embedding_cache(
        args.embedding_cache,
        matrix,
        asins,
        {
            "catalog_sha256": sha256_file(args.catalog),
            "model_id": args.model_id,
            "model_revision": revision,
            "device": args.device,
            "max_sequence_length": model.max_seq_length,
            "license": license_name,
            "library_versions": {
                "numpy": np.__version__,
                "torch": torch.__version__,
                "transformers": transformers.__version__,
                "sentence_transformers": sentence_transformers.__version__,
            },
        },
    )
    print(json.dumps(manifest.to_dict(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
