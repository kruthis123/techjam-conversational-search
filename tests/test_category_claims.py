from __future__ import annotations

from copy import deepcopy
import unittest

from starter.category_claims import CategoryClaim, category_claims


class CategoryClaimTest(unittest.TestCase):
    def test_categories_return_source_ordered_claims(self) -> None:
        record = {"parent_asin": "A", "categories": ["Clothing", "Shoes"]}

        self.assertEqual(
            category_claims(record),
            (
                CategoryClaim("A", "clothing", "categories"),
                CategoryClaim("A", "shoes", "categories"),
            ),
        )

    def test_normalizes_and_removes_repeated_categories(self) -> None:
        record = {
            "parent_asin": "A",
            "categories": [" Shoes ", "CLOTHING", "shoes", " Clothing "],
        }

        self.assertEqual(
            category_claims(record),
            (CategoryClaim("A", "shoes"), CategoryClaim("A", "clothing")),
        )

    def test_raw_record_is_unchanged(self) -> None:
        record = {
            "parent_asin": "A",
            "categories": [" Shoes ", "SHOES"],
            "details": {"color": "blue"},
        }
        original = deepcopy(record)

        category_claims(record)

        self.assertEqual(record, original)


if __name__ == "__main__":
    unittest.main()
