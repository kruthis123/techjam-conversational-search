from __future__ import annotations

import unittest

from starter.fusion import (
    FusedCandidate,
    RouteEvidence,
    apply_candidate_budget,
    fuse_candidates,
)
from starter.retrieval import RetrievalHit


class FuseCandidatesTest(unittest.TestCase):
    def test_deduplicates_candidates_and_combines_route_support(self) -> None:
        candidates = fuse_candidates(
            {
                "bm25": (
                    RetrievalHit("SHARED", 1, 8.5),
                    RetrievalHit("BM25_ONLY", 2, 4.0),
                ),
                "facet": (RetrievalHit("SHARED", 2, 2.0),),
                "svd_256": (RetrievalHit("SVD_ONLY", 1, 0.75),),
            }
        )

        self.assertEqual(
            tuple(candidate.parent_asin for candidate in candidates),
            ("SHARED", "SVD_ONLY", "BM25_ONLY"),
        )
        self.assertAlmostEqual(candidates[0].score, 1 / 61 + 1 / 62)
        self.assertEqual(
            candidates[0].route_evidence,
            (
                RouteEvidence("bm25", 1, 8.5),
                RouteEvidence("facet", 2, 2.0),
            ),
        )

    def test_uses_parent_asin_to_break_equal_score_ties(self) -> None:
        candidates = fuse_candidates(
            {
                "bm25": (RetrievalHit("B", 1, 5.0),),
                "facet": (RetrievalHit("A", 1, 1.0),),
            }
        )

        self.assertEqual(
            candidates,
            (
                FusedCandidate("A", 1 / 61, (RouteEvidence("facet", 1, 1.0),)),
                FusedCandidate("B", 1 / 61, (RouteEvidence("bm25", 1, 5.0),)),
            ),
        )

    def test_equal_rank_multisets_tie_across_route_permutations(self) -> None:
        candidates = fuse_candidates(
            {
                "route_1": (
                    RetrievalHit("A", 1, 3.0),
                    RetrievalHit("B", 7, 1.0),
                ),
                "route_2": (
                    RetrievalHit("B", 1, 3.0),
                    RetrievalHit("A", 2, 2.0),
                ),
                "route_3": (
                    RetrievalHit("B", 2, 2.0),
                    RetrievalHit("A", 7, 1.0),
                ),
            }
        )

        self.assertEqual(tuple(candidate.parent_asin for candidate in candidates), ("A", "B"))
        self.assertEqual(candidates[0].score, candidates[1].score)

    def test_returns_empty_tuple_when_routes_have_no_hits(self) -> None:
        self.assertEqual(fuse_candidates({"bm25": (), "facet": ()}), ())


class ApplyCandidateBudgetTest(unittest.TestCase):
    def setUp(self) -> None:
        self.candidates = (
            FusedCandidate("A", 0.3, (RouteEvidence("bm25", 1, 8.5),)),
            FusedCandidate("B", 0.2, (RouteEvidence("facet", 1, 2.0),)),
            FusedCandidate("C", 0.1, (RouteEvidence("svd_256", 1, 0.75),)),
        )

    def test_limits_candidates_without_changing_order_or_evidence(self) -> None:
        limited = apply_candidate_budget(self.candidates, 2)

        self.assertEqual(limited, self.candidates[:2])

    def test_returns_complete_union_when_limit_is_larger(self) -> None:
        self.assertEqual(apply_candidate_budget(self.candidates, 10), self.candidates)

    def test_returns_empty_tuple_when_limit_is_zero(self) -> None:
        self.assertEqual(apply_candidate_budget(self.candidates, 0), ())


if __name__ == "__main__":
    unittest.main()
