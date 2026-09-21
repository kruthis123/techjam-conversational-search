from __future__ import annotations

from copy import deepcopy
import unittest

from starter.price_claims import PriceClaim, price_claim


class PriceClaimTest(unittest.TestCase):
    def test_numeric_price_returns_source_linked_claim(self) -> None:
        for value in (42, 19.99):
            with self.subTest(value=value):
                claim = price_claim({"parent_asin": "A", "price": value})

                self.assertEqual(claim, PriceClaim("A", value, "price"))
                self.assertIs(type(claim.value), type(value))

    def test_missing_null_string_and_boolean_prices_return_none(self) -> None:
        records = [
            {"parent_asin": "A"},
            {"parent_asin": "A", "price": None},
            {"parent_asin": "A", "price": "—"},
            {"parent_asin": "A", "price": "from 19.99"},
            {"parent_asin": "A", "price": True},
        ]

        for record in records:
            with self.subTest(record=record):
                self.assertIsNone(price_claim(record))

    def test_raw_record_is_unchanged_on_both_paths(self) -> None:
        records = [
            {"parent_asin": "A", "price": 19.99, "details": {"color": "blue"}},
            {"parent_asin": "B", "price": "—", "details": {"color": "red"}},
        ]

        for record in records:
            with self.subTest(record=record):
                original = deepcopy(record)
                price_claim(record)
                self.assertEqual(record, original)


if __name__ == "__main__":
    unittest.main()
