from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from experiments.prepare_m4_split import prepare_split, sha256_file


class PrepareM4SplitTest(unittest.TestCase):
    def test_prepares_deterministic_separate_partitions_and_manifest(self) -> None:
        samples = [
            {
                "sample_id": f"{scenario}-{index}",
                "scenario_type": scenario,
            }
            for scenario in ("buying", "browsing", "intent_override", "boundary")
            for index in range(5)
        ]

        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "public.jsonl"
            tuning = root / "data" / "tuning.jsonl"
            holdout = root / "secure" / "holdout.jsonl"
            manifest_path = root / "manifest.json"
            source.write_text(
                "".join(json.dumps(sample) + "\n" for sample in samples),
                encoding="utf-8",
            )

            manifest = prepare_split(source, tuning, holdout, manifest_path)
            first_tuning = tuning.read_bytes()
            first_holdout = holdout.read_bytes()
            repeated = prepare_split(source, tuning, holdout, manifest_path)

            self.assertEqual(tuning.read_bytes(), first_tuning)
            self.assertEqual(holdout.read_bytes(), first_holdout)
            self.assertEqual(repeated, manifest)
            self.assertEqual(manifest["source"]["sample_count"], 20)
            self.assertEqual(manifest["partitions"]["tuning"]["sample_count"], 16)
            self.assertEqual(manifest["partitions"]["holdout"]["sample_count"], 4)
            self.assertEqual(
                manifest["partitions"]["tuning"]["sha256"],
                sha256_file(tuning),
            )
            self.assertEqual(
                manifest["partitions"]["holdout"]["sha256"],
                sha256_file(holdout),
            )
            tuning_ids = set(manifest["partitions"]["tuning"]["sample_ids"])
            holdout_ids = set(manifest["partitions"]["holdout"]["sample_ids"])
            self.assertFalse(tuning_ids & holdout_ids)
            self.assertEqual(tuning_ids | holdout_ids, {s["sample_id"] for s in samples})


if __name__ == "__main__":
    unittest.main()
