from __future__ import annotations

from dataclasses import FrozenInstanceError
import unittest

from starter.intent import ObservedClaim
from starter.retrieval import RetrievalHit, build_retrieval_query


class BuildRetrievalQueryTest(unittest.TestCase):
    def test_joins_required_and_preferred_values_in_stored_order(self) -> None:
        claims = (
            ObservedClaim("category", "hiking shoes", "required"),
            ObservedClaim("material", "nylon", "preferred"),
        )

        self.assertEqual(build_retrieval_query(claims), "hiking shoes nylon")

    def test_ignores_indifferent_blank_and_repeated_values(self) -> None:
        claims = (
            ObservedClaim("category", " handbags ", "required"),
            ObservedClaim("material", "leather", "indifferent"),
            ObservedClaim("color", "   ", "preferred"),
            ObservedClaim("feature", "handbags", "preferred"),
            ObservedClaim("style", None, "indifferent"),
        )

        self.assertEqual(build_retrieval_query(claims), "handbags")


class RetrievalHitTest(unittest.TestCase):
    def test_exposes_route_local_values_and_is_immutable(self) -> None:
        hit = RetrievalHit(parent_asin="A", rank=1, score=0.75)

        self.assertEqual(hit.parent_asin, "A")
        self.assertEqual(hit.rank, 1)
        self.assertEqual(hit.score, 0.75)
        with self.assertRaises(FrozenInstanceError):
            hit.rank = 2

    def test_rejects_rank_zero(self) -> None:
        with self.assertRaisesRegex(ValueError, "rank must be at least 1"):
            RetrievalHit(parent_asin="A", rank=0, score=0.75)


if __name__ == "__main__":
    unittest.main()
