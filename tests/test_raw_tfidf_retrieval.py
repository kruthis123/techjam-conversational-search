from __future__ import annotations

import unittest

from starter.raw_tfidf_retrieval import RawTfidfRetriever


class RawTfidfRetrieverTest(unittest.TestCase):
    def test_uses_field_labelled_documents_and_20k_feature_limit(self) -> None:
        retriever = RawTfidfRetriever({
            "A": {
                "title": "trailblazer",
                "categories": ["outerwear"],
                "features": ["packable"],
                "details": {"lining": {"material": "fleece"}},
                "store": "northwind",
                "description": ["stormproof"],
            },
            "B": {"title": "summer sandals"},
        })

        self.assertEqual(retriever._vectorizer.max_features, 20_000)
        for term in (
            "title",
            "categories",
            "features",
            "details",
            "store",
            "description",
            "trailblazer",
            "outerwear",
            "packable",
            "fleece",
            "northwind",
            "stormproof",
        ):
            with self.subTest(term=term):
                self.assertIn(term, retriever._vectorizer.vocabulary_)

    def test_cosine_similarity_ranks_relevant_product_first(self) -> None:
        retriever = RawTfidfRetriever({
            "A": {"title": "waterproof hiking boots"},
            "B": {"title": "silk evening dress"},
            "C": {"title": "cotton office shirt"},
        })

        hits = retriever.search("waterproof hiking", depth=2)

        self.assertEqual([hit.parent_asin for hit in hits], ["A", "B"])
        self.assertEqual([hit.rank for hit in hits], [1, 2])
        self.assertGreater(hits[0].score, hits[1].score)

    def test_equal_scores_use_parent_asin_tie_break_and_depth(self) -> None:
        retriever = RawTfidfRetriever({
            "B": {"title": "shared hiking shoe"},
            "A": {"title": "shared hiking shoe"},
            "C": {"title": "formal dress"},
        })

        hits = retriever.search("shared hiking", depth=1)

        self.assertEqual([hit.parent_asin for hit in hits], ["A"])
        self.assertEqual(hits[0].rank, 1)

    def test_empty_oov_and_zero_depth_return_no_hits(self) -> None:
        retriever = RawTfidfRetriever({
            "A": {"title": "hiking boots"},
            "B": {"title": "running shoes"},
        })

        self.assertEqual(retriever.search("", depth=10), ())
        self.assertEqual(retriever.search("unseenword", depth=10), ())
        self.assertEqual(retriever.search("hiking", depth=0), ())


if __name__ == "__main__":
    unittest.main()
