from __future__ import annotations

import argparse
import json
from pathlib import Path

import sentence_transformers
import torch
import transformers
from huggingface_hub import HfApi
from sentence_transformers import CrossEncoder

from starter.catalog_cache import sha256_file
from starter.reranking import (
    L4_MODEL_DIRECTORY,
    L4_MODEL_ID,
    L6_MODEL_DIRECTORY,
    L6_MODEL_ID,
    RERANK_MANIFEST_FILE,
)


MODELS = {
    "l4": (L4_MODEL_ID, L4_MODEL_DIRECTORY),
    "l6": (L6_MODEL_ID, L6_MODEL_DIRECTORY),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download and save a pinned local cross-encoder reranker."
    )
    parser.add_argument("--model", choices=tuple(MODELS), default="l4")
    parser.add_argument("--revision", help="Optional Hugging Face commit or tag.")
    parser.add_argument("--model-directory")
    parser.add_argument("--device", default="cpu")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model_id, default_directory = MODELS[args.model]
    model_directory = Path(args.model_directory or default_directory)
    info = HfApi().model_info(model_id, revision=args.revision)
    revision = str(info.sha)
    print(f"Loading {model_id} at revision {revision}")
    model = CrossEncoder(model_id, revision=revision, device=args.device)
    model_directory.parent.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(model_directory), safe_serialization=True)

    weight_path = model_directory / "model.safetensors"
    if not weight_path.is_file():
        weight_path = model_directory / "pytorch_model.bin"
    if not weight_path.is_file():
        raise RuntimeError("saved reranker does not contain a recognized weight file")

    card_data = getattr(info, "card_data", None)
    manifest = {
        "model_id": model_id,
        "model_revision": revision,
        "license": getattr(card_data, "license", None) or "unknown",
        "max_length": int(model.max_seq_length or 512),
        "device": args.device,
        "weight_file": weight_path.name,
        "weight_sha256": sha256_file(weight_path),
        "weight_size_bytes": weight_path.stat().st_size,
        "library_versions": {
            "torch": torch.__version__,
            "transformers": transformers.__version__,
            "sentence_transformers": sentence_transformers.__version__,
        },
    }
    manifest_path = model_directory / RERANK_MANIFEST_FILE
    temporary = manifest_path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(manifest_path)
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
