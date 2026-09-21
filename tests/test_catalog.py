from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import tomllib
import unittest

from starter.catalog import load_catalog


ROOT = Path(__file__).resolve().parents[1]


class CatalogTest(unittest.TestCase):
    def write_lines(self, directory: str, lines: list[str]) -> Path:
        path = Path(directory) / "catalog.jsonl"
        path.write_text("".join(lines), encoding="utf-8")
        return path

    def assert_content_error(self, path: Path, line_number: int) -> None:
        with self.assertRaises(ValueError) as raised:
            load_catalog(path)
        message = str(raised.exception)
        self.assertIn(str(path), message)
        self.assertIn(f"line {line_number}", message)

    def test_loads_complete_raw_records_in_file_order(self) -> None:
        expected = [
            {
                "parent_asin": "A",
                "title": "First",
                "features": ["soft", None],
                "details": {"dimensions": {"width": 3.5}},
                "price": "19.99",
            },
            {
                "parent_asin": "B",
                "title": "Second",
                "categories": ["Clothing", "Shoes"],
                "price": 42,
                "store": None,
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_lines(
                directory,
                [json.dumps(record) + "\n" for record in expected],
            )

            records = load_catalog(path)

        self.assertEqual(list(records), ["A", "B"])
        self.assertEqual(records, {"A": expected[0], "B": expected[1]})

    def test_empty_file_returns_empty_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_lines(directory, [])
            self.assertEqual(load_catalog(path), {})

    def test_malformed_json_reports_path_and_physical_line(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_lines(
                directory,
                ['{"parent_asin": "A"}\n', "\n", "{not json}\n"],
            )
            self.assert_content_error(path, 3)

    def test_non_object_rows_report_path_and_line(self) -> None:
        for invalid_row in ("[]", '"value"', "7", "null"):
            with self.subTest(invalid_row=invalid_row):
                with tempfile.TemporaryDirectory() as directory:
                    path = self.write_lines(directory, [invalid_row + "\n"])
                    self.assert_content_error(path, 1)

    def test_invalid_parent_asin_reports_path_and_line(self) -> None:
        invalid_records = [
            {},
            {"parent_asin": None},
            {"parent_asin": 123},
            {"parent_asin": ""},
            {"parent_asin": "   "},
        ]
        for invalid_record in invalid_records:
            with self.subTest(invalid_record=invalid_record):
                with tempfile.TemporaryDirectory() as directory:
                    path = self.write_lines(
                        directory,
                        [json.dumps(invalid_record) + "\n"],
                    )
                    self.assert_content_error(path, 1)

    def test_duplicate_parent_asin_reports_later_line(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_lines(
                directory,
                [
                    '{"parent_asin": "A", "title": "First"}\n',
                    '{"parent_asin": "A", "title": "Second"}\n',
                ],
            )
            self.assert_content_error(path, 2)

    def test_missing_file_raises_file_not_found_with_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.jsonl"
            with self.assertRaises(FileNotFoundError) as raised:
                load_catalog(path)
            self.assertIn(str(path), str(raised.exception))

    def test_official_catalog_loads_without_changing_its_digest(self) -> None:
        path = ROOT / "data" / "catalog.jsonl"
        digest_before = hashlib.sha256(path.read_bytes()).hexdigest()

        records = load_catalog(path)

        digest_after = hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual(len(records), 50_000)
        self.assertEqual(len(records), len(set(records)))
        self.assertEqual(
            digest_before,
            "da979b05a68af864cb0dcf9ee6a81c010c7e66a57978ad286c7a2e005fc69a67",
        )
        self.assertEqual(digest_after, digest_before)

    def test_manifest_pins_python_and_has_no_runtime_dependencies(self) -> None:
        manifest = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(manifest["project"]["requires-python"], ">=3.12,<3.13")
        self.assertEqual(manifest["project"].get("dependencies", []), [])


if __name__ == "__main__":
    unittest.main()
