"""Validate a built submission archive and run it in forced-offline mode."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARCHIVE = ROOT / "dist" / "techjam-shopping-agent.zip"
DEFAULT_CATALOG = ROOT / "data" / "catalog.jsonl"
EXPECTED_CATALOG_SHA256 = "da979b05a68af864cb0dcf9ee6a81c010c7e66a57978ad286c7a2e005fc69a67"
REQUIRED_FILES = {
    "agent.py",
    "README.md",
    "REPORT.md",
    "requirements.txt",
    "MANIFEST.json",
    "starter/agent.py",
    "models/cross-encoder-ms-marco-MiniLM-L4-v2/model.safetensors",
    "models/cross-encoder-ms-marco-MiniLM-L4-v2/reranker_manifest.json",
}
DISALLOWED_NAMES = {
    ".env",
    "data/catalog.jsonl",
    "data/public_set.jsonl",
    "results.json",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_archive(archive_path: Path) -> dict[str, object]:
    with zipfile.ZipFile(archive_path) as archive:
        names = set(archive.namelist())
        unsafe = [
            name
            for name in names
            if Path(name).is_absolute() or ".." in Path(name).parts
        ]
        if unsafe:
            raise ValueError(f"Unsafe archive paths: {unsafe}")
        missing = sorted(REQUIRED_FILES - names)
        if missing:
            raise ValueError(f"Missing required files: {missing}")
        forbidden = sorted(name for name in names if name in DISALLOWED_NAMES)
        forbidden.extend(
            sorted(
                name
                for name in names
                if name.startswith(("experiments/", "evaluator/", ".git/"))
            )
        )
        if forbidden:
            raise ValueError(f"Disallowed files in archive: {forbidden}")

        manifest = json.loads(archive.read("MANIFEST.json"))
        if manifest.get("entry_point") != "agent:Agent":
            raise ValueError("Unexpected Agent entry point")
        if manifest.get("network_required") is not False:
            raise ValueError("Submission must declare offline inference")
        if manifest.get("catalog_included") is not False:
            raise ValueError("Catalog must not be included")
        declared_files = manifest.get("files")
        if not isinstance(declared_files, dict):
            raise ValueError("Manifest files section is invalid")
        if set(declared_files) != names - {"MANIFEST.json"}:
            raise ValueError("Manifest file list does not match the archive")
        for name, metadata in declared_files.items():
            content = archive.read(name)
            if not isinstance(metadata, dict):
                raise ValueError(f"Invalid manifest record: {name}")
            if metadata.get("size_bytes") != len(content):
                raise ValueError(f"Size mismatch: {name}")
            if metadata.get("sha256") != hashlib.sha256(content).hexdigest():
                raise ValueError(f"Checksum mismatch: {name}")
        return manifest


def run_offline_smoke(archive_path: Path, catalog_path: Path) -> dict[str, object]:
    smoke_program = """
import json
import sys
from agent import Agent

catalog = sys.argv[1]
agent = Agent(catalog)
session_id = "submission_readiness"
agent.reset(session_id, {
    "purchase_frequency": "occasional",
    "average_prior_rating": 4.2,
    "rating_style": "balanced",
    "preference_tags": ["comfort", "durable"],
    "summary": "Prefers comfortable and durable products.",
})
messages = [
    "I'm looking for footwear, but I'm still exploring.",
    "Women's slippers for home, under $40.",
    "Actually, ignore slippers. I need men's waterproof hiking boots under $120.",
]
responses = []
for turn, message in enumerate(messages, start=1):
    response = agent.respond(session_id, message, turn, 10)
    responses.append(response)
print(json.dumps({"responses": responses, "trace": agent.get_last_trace(session_id)}))
"""
    with tempfile.TemporaryDirectory(prefix="techjam-submission-") as temporary:
        root = Path(temporary)
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(root)
        environment = os.environ.copy()
        environment.update(
            {
                "HF_HUB_OFFLINE": "1",
                "TRANSFORMERS_OFFLINE": "1",
                "PYTHONNOUSERSITE": "1",
            }
        )
        result = subprocess.run(
            [sys.executable, "-c", smoke_program, str(catalog_path.resolve())],
            cwd=root,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        payload = json.loads(result.stdout)

    catalog_ids = set()
    with catalog_path.open(encoding="utf-8") as handle:
        for line in handle:
            catalog_ids.add(str(json.loads(line)["parent_asin"]))
    for response in payload["responses"]:
        validate_response(response, catalog_ids)
    trace = payload.get("trace", {})
    if trace.get("fallback_used"):
        raise ValueError(f"Offline smoke used fallback: {trace.get('warnings')}")
    return {
        "turns": len(payload["responses"]),
        "recommendation_counts": [
            len(response["recommendations"]) for response in payload["responses"]
        ],
        "final_route": trace.get("inferred_route"),
        "search_revision": trace.get("search_revision"),
        "fallback_used": trace.get("fallback_used"),
    }


def validate_response(response: object, catalog_ids: set[str]) -> None:
    if not isinstance(response, dict):
        raise ValueError("Response is not an object")
    if set(response) != {"message", "ask_attribute", "recommendations", "usage"}:
        raise ValueError("Response fields do not match the contract")
    if not isinstance(response["message"], str):
        raise ValueError("Response message is not a string")
    recommendations = response["recommendations"]
    if not isinstance(recommendations, list) or len(recommendations) > 10:
        raise ValueError("Invalid recommendation list")
    identifiers = [item.get("parent_asin") for item in recommendations]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("Duplicate recommendation IDs")
    if any(identifier not in catalog_ids for identifier in identifiers):
        raise ValueError("Recommendation is not in the catalog")
    usage = response["usage"]
    if usage != {"prompt_tokens": 0, "completion_tokens": 0}:
        raise ValueError("Unexpected local token usage")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--skip-smoke", action="store_true")
    args = parser.parse_args()

    if sys.version_info[:2] != (3, 12):
        raise RuntimeError("Submission is tested only with Python 3.12")
    if sha256_file(args.catalog) != EXPECTED_CATALOG_SHA256:
        raise ValueError("Catalog checksum does not match the frozen catalog")
    manifest = inspect_archive(args.archive)
    report: dict[str, object] = {
        "archive": str(args.archive.resolve()),
        "archive_size_bytes": args.archive.stat().st_size,
        "archive_sha256": sha256_file(args.archive),
        "file_count": len(manifest["files"]),
        "catalog_sha256": EXPECTED_CATALOG_SHA256,
        "manifest": "valid",
    }
    if not args.skip_smoke:
        report["offline_smoke"] = run_offline_smoke(args.archive, args.catalog)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
