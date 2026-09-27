from __future__ import annotations

import unittest

from starter.lexical_retrieval import LexicalRetriever


class LexicalRetrieverTest(unittest.TestCase):
    def test_stronger_any_token_match_ranks_first(self) -> None:
        retriever = LexicalRetriever({
            "B": {"title": "waterproof boots"},
            "A": {"title": "waterproof hiking boots"},
        })

        hits = retriever.search("waterproof, hiking!", depth=10)

        self.assertEqual([hit.parent_asin for hit in hits], ["A", "B"])
        self.assertEqual([hit.rank for hit in hits], [1, 2])
        self.assertGreater(hits[0].score, hits[1].score)

    def test_all_text_fields_and_nested_values_are_searchable(self) -> None:
        retriever = LexicalRetriever({
            "A": {
                "title": "trailblazer",
                "categories": ["outerwear"],
                "features": ["packable"],
                "details": {"lining": {"material": "fleece"}},
                "store": "northwind",
                "description": ["stormproof"],
            },
        })

        for query in (
            "trailblazer",
            "outerwear",
            "packable",
            "fleece",
            "northwind",
            "stormproof",
        ):
            with self.subTest(query=query):
                self.assertEqual(
                    [hit.parent_asin for hit in retriever.search(query, depth=1)],
                    ["A"],
                )

    def test_equal_scores_use_parent_asin_tie_break(self) -> None:
        retriever = LexicalRetriever({
            "B": {"title": "shared"},
            "A": {"title": "shared"},
        })

        hits = retriever.search("shared", depth=10)

        self.assertEqual([hit.parent_asin for hit in hits], ["A", "B"])
        self.assertEqual(hits[0].score, hits[1].score)

    def test_empty_query_and_zero_depth_return_no_hits(self) -> None:
        retriever = LexicalRetriever({"A": {"title": "boots"}})

        self.assertEqual(retriever.search("", depth=10), ())
        self.assertEqual(retriever.search("boots", depth=0), ())


if __name__ == "__main__":
    unittest.main()
