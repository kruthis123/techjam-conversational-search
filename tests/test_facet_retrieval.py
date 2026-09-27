from __future__ import annotations

import unittest

from starter.facet_retrieval import FacetRetriever


class FacetRetrieverTest(unittest.TestCase):
    def test_more_distinct_category_tokens_rank_first(self) -> None:
        retriever = FacetRetriever({
            "C": {"parent_asin": "C", "categories": ["Hiking"]},
            "B": {"parent_asin": "B", "categories": ["Shoes"]},
            "A": {
                "parent_asin": "A",
                "categories": ["Women's Shoes", "Hiking Gear"],
            },
        })

        hits = retriever.search("HIKING, shoes!", depth=10)

        self.assertEqual([hit.parent_asin for hit in hits], ["A", "B", "C"])
        self.assertEqual([hit.rank for hit in hits], [1, 2, 3])
        self.assertEqual([hit.score for hit in hits], [2.0, 1.0, 1.0])

    def test_repeated_query_and_category_tokens_count_once(self) -> None:
        retriever = FacetRetriever({
            "A": {
                "parent_asin": "A",
                "categories": ["Shoes Shoes", "SHOES"],
            },
        })

        hits = retriever.search("shoes shoes", depth=10)

        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].score, 1.0)

    def test_equal_scores_use_parent_asin_tie_break_and_depth(self) -> None:
        retriever = FacetRetriever({
            "B": {"parent_asin": "B", "categories": ["Shoes"]},
            "A": {"parent_asin": "A", "categories": ["Shoes"]},
        })

        hits = retriever.search("shoes", depth=1)

        self.assertEqual([hit.parent_asin for hit in hits], ["A"])
        self.assertEqual(hits[0].rank, 1)

    def test_no_match_empty_query_and_zero_depth_return_no_hits(self) -> None:
        retriever = FacetRetriever({
            "A": {"parent_asin": "A", "categories": ["Shoes"]},
        })

        self.assertEqual(retriever.search("hats", depth=10), ())
        self.assertEqual(retriever.search("", depth=10), ())
        self.assertEqual(retriever.search("shoes", depth=0), ())


if __name__ == "__main__":
    unittest.main()
