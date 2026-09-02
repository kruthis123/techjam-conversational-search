"""Build the deterministic, self-contained hackathon submission archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIRECTORY = ROOT / "submission"
MODEL_DIRECTORY = ROOT / "models" / "cross-encoder-ms-marco-MiniLM-L4-v2"
DEFAULT_OUTPUT = ROOT / "dist" / "techjam-shopping-agent.zip"
FIXED_ZIP_TIME = (2026, 8, 30, 0, 0, 0)

TEMPLATE_FILES = ("agent.py", "demo.py", "README.md", "REPORT.md", "requirements.txt")
DISALLOWED_PARTS = {
    ".env",
    ".git",
    "__pycache__",
    "catalog.jsonl",
    "public_set.jsonl",
    "results.json",
    "experiments",
    "evaluator",
}


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def submission_files() -> dict[str, Path]:
    """Return the explicit source allowlist keyed by archive path."""
    files = {name: TEMPLATE_DIRECTORY / name for name in TEMPLATE_FILES}
    files.update(
        {
            f"starter/{path.name}": path
            for path in sorted((ROOT / "starter").glob("*.py"))
        }
    )
    files.update(
        {
            f"models/{MODEL_DIRECTORY.name}/{path.name}": path
            for path in sorted(MODEL_DIRECTORY.glob("*"))
            if path.is_file()
        }
    )
    return dict(sorted(files.items()))


def validate_files(files: dict[str, Path]) -> None:
    missing = [archive_path for archive_path, path in files.items() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing submission files: {', '.join(missing)}")
    for archive_path in files:
        parts = set(Path(archive_path).parts)
        if parts & DISALLOWED_PARTS:
            raise ValueError(f"Disallowed submission path: {archive_path}")


def build_manifest(contents: dict[str, bytes]) -> bytes:
    files = {
        path: {"sha256": sha256_bytes(content), "size_bytes": len(content)}
        for path, content in sorted(contents.items())
    }
    manifest = {
        "name": "techjam-shopping-agent",
        "version": "1.0.0",
        "entry_point": "agent:Agent",
        "python": "3.12",
        "network_required": False,
        "catalog_included": False,
        "catalog_sha256": "da979b05a68af864cb0dcf9ee6a81c010c7e66a57978ad286c7a2e005fc69a67",
        "configuration": {
            "policy": "always_10",
            "retrieval": "multi_route_structured",
            "dense": "dense_off",
            "reranker": "minilm_l4_blended",
            "reranker_depth": 60,
            "semantic_weight": 0.25,
            "orchestration": "adaptive_cutoff",
        },
        "files": files,
    }
    return (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")


def build_archive(output_path: str | Path = DEFAULT_OUTPUT) -> Path:
    files = submission_files()
    validate_files(files)
    contents = {name: path.read_bytes() for name, path in files.items()}
    contents["MANIFEST.json"] = build_manifest(contents)

    output = Path(output_path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    with zipfile.ZipFile(
        temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for name, content in sorted(contents.items()):
            info = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content)
    temporary.replace(output)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = build_archive(args.output)
    print(
        json.dumps(
            {
                "archive": str(output),
                "size_bytes": output.stat().st_size,
                "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
