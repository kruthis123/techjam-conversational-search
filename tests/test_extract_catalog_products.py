from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from experiments.extract_catalog_products import SAVED_PARENT_ASINS


ROOT = Path(__file__).resolve().parents[1]


class ExtractCatalogProductsTest(unittest.TestCase):
    PRODUCTS = [
        {
            "parent_asin": "A",
            "title": "First",
            "features": ["soft", "light"],
            "description": ["first description"],
            "details": {"material": "cotton"},
            "price": None,
            "average_rating": 4.5,
        },
        {
            "parent_asin": "B",
            "title": "Second",
            "features": ["waterproof"],
            "description": ["second description"],
            "details": {"dimensions": {"width": 3}},
            "price": 42,
            "store": "Example Store",
        },
    ]

    def write_catalog(self, directory: str) -> Path:
        path = Path(directory) / "catalog.jsonl"
        path.write_text(
            "".join(json.dumps(product) + "\n" for product in self.PRODUCTS),
            encoding="utf-8",
        )
        return path

    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "experiments.extract_catalog_products", *arguments],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_writes_requested_products_in_order_with_all_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            catalog_path = self.write_catalog(directory)
            output_path = Path(directory) / "selected.json"

            result = self.run_cli(
                "B",
                "A",
                "--catalog",
                str(catalog_path),
                "--output",
                str(output_path),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            output = output_path.read_text(encoding="utf-8")
            products = json.loads(output)
            self.assertEqual(products, [self.PRODUCTS[1], self.PRODUCTS[0]])
            self.assertTrue(output.startswith("[\n  {\n"))

    def test_excludes_only_requested_top_level_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            catalog_path = self.write_catalog(directory)
            output_path = Path(directory) / "selected.json"

            result = self.run_cli(
                "A",
                "B",
                "--catalog",
                str(catalog_path),
                "--output",
                str(output_path),
                "--exclude",
                "features",
                "description",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            products = json.loads(output_path.read_text(encoding="utf-8"))
            excluded = {"features", "description"}
            self.assertEqual(
                products,
                [
                    {
                        field: value
                        for field, value in product.items()
                        if field not in excluded
                    }
                    for product in self.PRODUCTS
                ],
            )

    def test_missing_asin_reports_error_without_writing_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            catalog_path = self.write_catalog(directory)
            output_path = Path(directory) / "selected.json"

            result = self.run_cli(
                "A",
                "MISSING",
                "--catalog",
                str(catalog_path),
                "--output",
                str(output_path),
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("MISSING", result.stderr)
            self.assertFalse(output_path.exists())

    def test_no_positional_asins_use_saved_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            catalog_path = Path(directory) / "catalog.jsonl"
            catalog_path.write_text(
                "".join(
                    json.dumps({"parent_asin": parent_asin}) + "\n"
                    for parent_asin in SAVED_PARENT_ASINS
                ),
                encoding="utf-8",
            )
            output_path = Path(directory) / "selected.json"

            result = self.run_cli(
                "--catalog",
                str(catalog_path),
                "--output",
                str(output_path),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            products = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(
                [product["parent_asin"] for product in products],
                SAVED_PARENT_ASINS,
            )

    def test_help_documents_arguments_without_loading_catalog(self) -> None:
        result = self.run_cli("--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("one or more parent_asin values in requested order", result.stdout)
        self.assertIn(
            "JSONL catalog path (default: data/catalog.jsonl)", result.stdout
        )
        self.assertIn("required output path for the indented JSON array", result.stdout)
        self.assertIn("zero or more top-level field names to omit", result.stdout)


if __name__ == "__main__":
    unittest.main()
