from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from evaluator.local_evaluator import load_jsonl
from experiments.m3_compare_routes import stratified_split


SPLIT_ID = "m4-public-scenario-stratified-80-20-v1"
SPLIT_METHOD = (
    "Within each scenario, order by SHA-256(sample_id) then sample_id; "
    "assign the first floor(4n/5) sessions to tuning and the rest to holdout."
)
SEED_STATEMENT = "No random seed; membership is deterministic from sample IDs."


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_jsonl(path: Path, samples: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "".join(
        json.dumps(sample, sort_keys=True, separators=(",", ":")) + "\n"
        for sample in samples
    )
    path.write_text(content, encoding="utf-8")


def prepare_split(
    source_path: Path,
    tuning_path: Path,
    holdout_path: Path,
    manifest_path: Path,
) -> dict:
    samples = load_jsonl(source_path)
    tuning, holdout = stratified_split(samples)
    write_jsonl(tuning_path, tuning)
    write_jsonl(holdout_path, holdout)

    manifest = {
        "split_id": SPLIT_ID,
        "method": SPLIT_METHOD,
        "seed_statement": SEED_STATEMENT,
        "source": {
            "path": str(source_path),
            "sample_count": len(samples),
            "sha256": sha256_file(source_path),
        },
        "partitions": {
            "tuning": {
                "path": str(tuning_path),
                "sample_count": len(tuning),
                "sample_ids": [str(sample["sample_id"]) for sample in tuning],
                "sha256": sha256_file(tuning_path),
            },
            "holdout": {
                "path": str(holdout_path),
                "sample_count": len(holdout),
                "sample_ids": [str(sample["sample_id"]) for sample in holdout],
                "sha256": sha256_file(holdout_path),
            },
        },
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Materialize the fixed M4 tuning and protected holdout files once"
    )
    parser.add_argument("--source", default="data/public_set.jsonl")
    parser.add_argument("--tuning-output", default="data/m4_tuning.jsonl")
    parser.add_argument("--holdout-output", default="secure/m4_holdout.jsonl")
    parser.add_argument("--manifest-output", default="data/m4_split_manifest.json")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    prepare_split(
        Path(args.source),
        Path(args.tuning_output),
        Path(args.holdout_output),
        Path(args.manifest_output),
    )


if __name__ == "__main__":
    main()
