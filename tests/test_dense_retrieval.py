from __future__ import annotations

import unittest

from starter.dense_retrieval import DenseRetriever


class DenseRetrieverTest(unittest.TestCase):
    def test_defaults_to_64_and_accepts_256_dimensions(self) -> None:
        records = {
            f"P{index}": {"title": f"product token{index}"}
            for index in range(257)
        }

        default = DenseRetriever(records)
        requested = DenseRetriever(records, dimensions=256)

        self.assertEqual(default._svd.n_components, 64)
        self.assertEqual(requested._svd.n_components, 256)

    def test_requested_dimensions_are_capped_to_matrix_shape(self) -> None:
        records = {
            "A": {"title": "red wool coat"},
            "B": {"title": "blue cotton shirt"},
            "C": {"title": "black leather boots"},
        }

        requested = DenseRetriever(records, dimensions=256)

        self.assertEqual(requested._svd.n_components, 3)

    def test_relevant_product_ranks_first(self) -> None:
        retriever = DenseRetriever({
            "A": {"title": "waterproof hiking boots"},
            "B": {"title": "silk evening dress"},
            "C": {"title": "cotton office shirt"},
        })

        hits = retriever.search("waterproof trail hiking", depth=2)

        self.assertEqual(hits[0].parent_asin, "A")
        self.assertEqual([hit.rank for hit in hits], [1, 2])
        self.assertGreaterEqual(hits[0].score, hits[1].score)

    def test_nested_and_list_text_fields_are_searchable(self) -> None:
        retriever = DenseRetriever({
            "A": {
                "categories": ["outerwear"],
                "features": ["packable"],
                "details": {"lining": {"material": "fleece"}},
                "store": "northwind",
                "description": ["winter jacket"],
            },
            "B": {"title": "summer sandals"},
            "C": {"title": "formal trousers"},
        })

        hits = retriever.search("fleece winter outerwear", depth=1)

        self.assertEqual(hits[0].parent_asin, "A")

    def test_equal_scores_use_parent_asin_tie_break_and_depth(self) -> None:
        retriever = DenseRetriever({
            "B": {"title": "shared hiking shoe"},
            "A": {"title": "shared hiking shoe"},
            "C": {"title": "formal dress"},
        })

        hits = retriever.search("shared hiking", depth=1)

        self.assertEqual([hit.parent_asin for hit in hits], ["A"])
        self.assertEqual(hits[0].rank, 1)

    def test_empty_oov_and_zero_depth_return_no_hits(self) -> None:
        retriever = DenseRetriever({
            "A": {"title": "hiking boots"},
            "B": {"title": "running shoes"},
        })

        self.assertEqual(retriever.search("", depth=10), ())
        self.assertEqual(retriever.search("unseenword", depth=10), ())
        self.assertEqual(retriever.search("hiking", depth=0), ())


if __name__ == "__main__":
    unittest.main()
