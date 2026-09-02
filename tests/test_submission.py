from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.check_submission import inspect_archive
from scripts.package_submission import build_archive, submission_files


class SubmissionPackagingTests(unittest.TestCase):
    def test_allowlist_excludes_data_evaluator_and_experiments(self) -> None:
        names = set(submission_files())

        self.assertIn("agent.py", names)
        self.assertIn("starter/agent.py", names)
        self.assertTrue(
            any(name.endswith("model.safetensors") for name in names)
        )
        self.assertFalse(any(name.startswith("data/") for name in names))
        self.assertFalse(any(name.startswith("evaluator/") for name in names))
        self.assertFalse(any(name.startswith("experiments/") for name in names))

    def test_built_archive_matches_its_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            archive_path = build_archive(Path(temporary) / "submission.zip")
            manifest = inspect_archive(archive_path)
            with zipfile.ZipFile(archive_path) as archive:
                wrapper = archive.read("agent.py").decode("utf-8")

        self.assertEqual(manifest["entry_point"], "agent:Agent")
        self.assertFalse(manifest["network_required"])
        self.assertIn("class Agent", wrapper)

    def test_manifest_freezes_selected_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            archive_path = build_archive(Path(temporary) / "submission.zip")
            with zipfile.ZipFile(archive_path) as archive:
                manifest = json.loads(archive.read("MANIFEST.json"))

        self.assertEqual(manifest["configuration"]["dense"], "dense_off")
        self.assertEqual(
            manifest["configuration"]["reranker"], "minilm_l4_blended"
        )
        self.assertEqual(
            manifest["configuration"]["orchestration"], "adaptive_cutoff"
        )


if __name__ == "__main__":
    unittest.main()
