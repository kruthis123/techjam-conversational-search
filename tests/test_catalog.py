from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from starter.catalog import Product, flatten_details, load_source_catalog, normalize_text
from starter.catalog_cache import (
    build_catalog_cache,
    get_cache_status,
    load_cached_catalog,
)


def _product(parent_asin: str, title: str, categories: list[str]) -> dict:
    return {
        "parent_asin": parent_asin,
        "title": title,
        "categories": categories,
        "features": [],
        "description": [],
        "details": {},
        "price": None,
        "average_rating": None,
        "rating_number": 0,
        "store": "Example",
    }


class CatalogTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.catalog_path = self.root / "catalog.jsonl"

    def tearDown(self) -> None:
        self.directory.cleanup()

    def _write(self, products: list[dict]) -> None:
        self.catalog_path.write_text(
            "".join(json.dumps(product) + "\n" for product in products),
            encoding="utf-8",
        )

    def test_normalization_and_nested_details(self) -> None:
        self.assertEqual(normalize_text("  Soft\u00a0&amp;   warm  "), "Soft & warm")
        self.assertEqual(
            flatten_details(
                {
                    "Brand": " Example ",
                    "Best Sellers Rank": {"Shoes": 12, "Clothing": 30},
                }
            ),
            (
                ("Brand", "Example"),
                ("Best Sellers Rank.Shoes", "12"),
                ("Best Sellers Rank.Clothing", "30"),
            ),
        )

    def test_product_extracts_brand_and_controlled_facets(self) -> None:
        product = Product.from_source(
            {
                "parent_asin": "A",
                "title": "Women's Grey Faux-Leather Slippers",
                "categories": ["Clothing", "Women", "Shoes", "Slippers"],
                "features": ["EVA sole", "100% cotton lining"],
                "description": ["Also available in navy blue and multi--color."],
                "details": {"Brand": "Acme"},
                "store": "Acme Store",
            }
        )
        self.assertEqual(product.brand, "Acme")
        self.assertEqual(product.colors, ("gray", "navy", "multicolor"))
        self.assertEqual(product.materials, ("cotton", "faux leather", "eva"))
        self.assertIn("Clothing > Women > Shoes > Slippers", product.categories_text)
        self.assertIn("Title: Women's Grey Faux-Leather Slippers", product.dense_text)

    def test_missing_optional_fields_are_allowed(self) -> None:
        product = Product.from_source({"parent_asin": "A"})
        self.assertEqual(product.title, "")
        self.assertEqual(product.categories, ())
        self.assertIsNone(product.price)
        self.assertEqual(product.lexical_text, "")

    def test_loader_preserves_order_and_builds_prefix_ontology(self) -> None:
        self._write(
            [
                _product("A", "Women's slippers", ["Clothing", "Women", "Shoes", "Slippers"]),
                _product("B", "Men's slippers", ["Clothing", "Men", "Shoes", "Slippers"]),
            ]
        )
        catalog = load_source_catalog(self.catalog_path)

        self.assertEqual(tuple(catalog.by_id), ("A", "B"))
        self.assertEqual(catalog.ontology.product_ids(()), ("A", "B"))
        self.assertEqual(catalog.ontology.product_ids(("Clothing", "Women")), ("A",))
        self.assertEqual(
            catalog.ontology.children(("Clothing",)),
            (("Clothing", "Women"), ("Clothing", "Men")),
        )

    def test_duplicate_ids_include_the_source_line(self) -> None:
        self._write(
            [
                _product("A", "First", ["Clothing"]),
                _product("A", "Second", ["Clothing"]),
            ]
        )
        with self.assertRaisesRegex(ValueError, "line 2: A"):
            load_source_catalog(self.catalog_path)

    def test_cache_round_trip_and_checksum_invalidation(self) -> None:
        products = [
            _product("A", "Black slippers", ["Clothing", "Women", "Shoes", "Slippers"]),
            _product("B", "Blue shoes", ["Clothing", "Men", "Shoes"]),
        ]
        self._write(products)
        cache_dir = self.root / "cache"

        original, _, _ = build_catalog_cache(self.catalog_path, cache_dir)
        status = get_cache_status(self.catalog_path, cache_dir)
        cached = load_cached_catalog(self.catalog_path, cache_dir)

        self.assertTrue(status.valid)
        self.assertEqual(cached.products, original.products)
        self.assertEqual(cached.ontology.product_ids(()), ("A", "B"))

        products[0]["title"] = "White slippers"
        self._write(products)
        changed_status = get_cache_status(self.catalog_path, cache_dir)
        self.assertFalse(changed_status.valid)
        self.assertEqual(changed_status.reason, "source_checksum_changed")


if __name__ == "__main__":
    unittest.main()
