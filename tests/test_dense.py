from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from starter.catalog import Product
from starter.dense import (
    DenseConfig,
    DenseDocumentCompiler,
    DenseQueryCompiler,
    DenseRetriever,
    ExactDenseIndex,
    DenseResult,
    FieldedDenseDocumentCompiler,
    load_embedding_cache,
    write_embedding_cache,
)
from starter.retrieval import (
    CandidateEvidence,
    LexicalQuery,
    RetrievalResult,
    RouteResult,
    fuse_lexical_and_dense,
    fuse_lexical_and_dense_rescue,
)
from starter.state import SessionState


class FakeEncoder:
    def __init__(self, vector: list[float]) -> None:
        self.vector = vector
        self.texts: list[str] = []

    def encode(
        self,
        texts,
        *,
        batch_size: int,
        normalize_embeddings: bool,
    ) -> object:
        self.texts = list(texts)
        return np.asarray([self.vector for _ in texts], dtype=np.float32)


def _manifest_fields(catalog_sha256: str) -> dict[str, object]:
    return {
        "catalog_sha256": catalog_sha256,
        "model_id": "test-model",
        "model_revision": "abc123",
        "device": "cpu",
        "max_sequence_length": 512,
        "license": "test",
        "library_versions": {"numpy": np.__version__},
    }


class DenseCompilerTest(unittest.TestCase):
    def test_document_compiler_uses_the_product_dense_text(self) -> None:
        product = Product.from_source(
            {
                "parent_asin": "A",
                "title": "Warm house slippers",
                "categories": ["Clothing", "Women", "Shoes", "Slippers"],
                "features": ["Fleece lined"],
                "description": ["For cold evenings"],
                "details": {"Brand": "Example"},
            }
        )

        text = DenseDocumentCompiler().compile(product)

        self.assertIn("Title: Warm house slippers", text)
        self.assertIn("Category: Clothing > Women > Shoes > Slippers", text)
        self.assertIn("Features: Fleece lined", text)

    def test_query_compiler_keeps_only_current_active_values(self) -> None:
        state = SessionState("session", {})
        state.record_turn(1, "I want black slippers")
        state.add_slot_value("category", "Slippers", turn=1, source_text="slippers")
        state.add_slot_value("color", "Black", turn=1, source_text="black")
        state.record_turn(2, "Actually make them blue")
        state.replace_slot(
            "color",
            ("Blue",),
            turn=2,
            source_text="make them blue",
            new_revision=True,
        )
        state.mark_no_preference(
            "brand",
            turn=2,
            source_text="any brand",
            clear_existing=False,
        )

        query = DenseQueryCompiler().compile(
            "Actually make them blue", state.retrieval_view()
        )

        self.assertIn("Category: slippers", query.text)
        self.assertIn("Color: blue", query.text)
        self.assertNotIn("black", query.text.casefold())
        self.assertNotIn("brand:", query.text.casefold())

    def test_multi_query_compiler_separates_intent_and_profile_views(self) -> None:
        state = SessionState(
            "session",
            {
                "preference_tags": ["comfort", "durability"],
                "summary": "Prior purchases favor outdoor products.",
            },
        )
        state.record_turn(1, "I need waterproof boots for winter trails")
        state.add_slot_value(
            "category", "boots", turn=1, source_text="boots", strength="hard"
        )
        state.add_slot_value(
            "feature", "waterproof", turn=1, source_text="waterproof"
        )

        queries = DenseQueryCompiler().compile_views(
            "I need waterproof boots for winter trails",
            state.retrieval_view(),
            include_profile=True,
        )
        by_name = {query.name: query.text for query in queries}

        self.assertEqual(
            tuple(query.name for query in queries),
            ("identity", "constraints", "scenario", "profile"),
        )
        self.assertIn("category: boots", by_name["identity"])
        self.assertIn("waterproof", by_name["constraints"])
        self.assertIn("winter trails", by_name["scenario"])
        self.assertIn("comfort", by_name["profile"])
        self.assertNotIn("comfort", by_name["constraints"])

    def test_fielded_document_compiler_separates_product_views(self) -> None:
        product = Product.from_source(
            {
                "parent_asin": "A",
                "title": "Black leather hiking boots",
                "categories": ["Clothing", "Women", "Shoes", "Boots"],
                "features": ["Waterproof", "Ankle support"],
                "description": ["For winter trails"],
                "details": {"Brand": "Example", "Material": "Leather"},
                "price": 79.0,
            }
        )
        compiler = FieldedDenseDocumentCompiler()

        identity = compiler.compile(product, "identity")
        attributes = compiler.compile(product, "attributes")
        needs = compiler.compile(product, "needs")

        self.assertIn("Black leather hiking boots", identity)
        self.assertIn("Category:", identity)
        self.assertIn("Materials: leather", attributes)
        self.assertIn("Price: 79.00", attributes)
        self.assertIn("winter trails", needs)
        self.assertNotIn("Price:", needs)
        with self.assertRaises(ValueError):
            compiler.compile(product, "unknown")


class ExactDenseIndexTest(unittest.TestCase):
    def test_search_returns_exact_top_k(self) -> None:
        index = ExactDenseIndex(
            ("A", "B", "C"),
            np.asarray([[1.0, 0.0], [0.8, 0.6], [0.0, 1.0]], dtype=np.float32),
        )

        ids, scores = index.search([1.0, 0.0], 2)

        self.assertEqual(ids, ("A", "B"))
        self.assertGreater(scores[0], scores[1])

    def test_equal_scores_use_catalog_order(self) -> None:
        index = ExactDenseIndex(
            ("first", "second", "third"),
            np.asarray([[1.0, 0.0], [1.0, 0.0], [0.0, 1.0]], dtype=np.float32),
        )

        ids, _ = index.search([1.0, 0.0], 1)

        self.assertEqual(ids, ("first",))


class DenseFusionTest(unittest.TestCase):
    def test_browsing_gives_dense_more_weight_than_buying(self) -> None:
        lexical = RetrievalResult(
            candidates=(CandidateEvidence("A", 1.0, {"current_message": 1}, {}),),
            routes=(RouteResult("current_message", ("A",), (1.0,)),),
            queries=(LexicalQuery("current_message", "shoes", ("shoes",), ()),),
            config_name="multi_route_structured",
        )
        dense = DenseResult(
            query=DenseQueryCompiler().compile(
                "winter trail footwear", _empty_state().retrieval_view()
            ),
            candidate_ids=("B", "A"),
            scores=(0.9, 0.8),
            model_id="test-model",
            model_revision="abc123",
            device="cpu",
            encode_latency_ms=1.0,
        )

        browsing = fuse_lexical_and_dense(
            lexical,
            dense,
            route="browsing",
            catalog_order={"A": 0, "B": 1},
        )
        buying = fuse_lexical_and_dense(
            lexical,
            dense,
            route="buying",
            catalog_order={"A": 0, "B": 1},
        )

        browsing_by_id = {item.parent_asin: item for item in browsing.candidates}
        buying_by_id = {item.parent_asin: item for item in buying.candidates}
        self.assertGreater(
            browsing_by_id["B"].route_contributions["dense"],
            buying_by_id["B"].route_contributions["dense"],
        )
        self.assertGreater(
            buying_by_id["A"].route_contributions["lexical_fused"],
            browsing_by_id["A"].route_contributions["lexical_fused"],
        )
        self.assertIn("current_message", browsing_by_id["A"].route_ranks)
        self.assertEqual(browsing.routes[-1].name, "dense")

    def test_rescue_fusion_verifies_hard_constraints(self) -> None:
        lexical = RetrievalResult(
            candidates=(
                CandidateEvidence("A", 1.0, {"current_message": 1}, {}),
                CandidateEvidence("B", 0.5, {"current_message": 2}, {}),
            ),
            routes=(RouteResult("current_message", ("A", "B"), (1.0, 0.5)),),
            queries=(),
            config_name="multi_route_structured",
        )
        query = DenseQueryCompiler().compile(
            "blue boots", _empty_state().retrieval_view()
        )
        dense = DenseResult(
            query=query,
            candidate_ids=("D", "C"),
            scores=(0.9, 0.8),
            model_id="test-model",
            model_revision="abc123",
            device="cpu",
            encode_latency_ms=1.0,
        )
        state = SessionState("verify", {})
        state.record_turn(1, "blue boots")
        state.add_slot_value(
            "color", "blue", turn=1, source_text="blue", strength="hard"
        )

        class FakeStructuredScorer:
            def score(self, parent_asin, state_view):
                if parent_asin == "D":
                    return -1.0, (), ("color",)
                return 1.0, ("color",), ()

        result = fuse_lexical_and_dense_rescue(
            lexical,
            dense,
            state=state.retrieval_view(),
            structured_scorer=FakeStructuredScorer(),
            catalog_order={"A": 0, "B": 1, "C": 2, "D": 3},
            rescue_depth=1,
            rerank_anchor_depth=1,
        )

        self.assertEqual(result.candidate_ids, ("A", "C", "B"))
        self.assertIn("color", result.candidates[1].matched_constraints)


def _empty_state() -> SessionState:
    state = SessionState("empty", {})
    state.record_turn(1, "hello")
    return state


class DenseCacheTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.matrix = np.asarray([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
        self.catalog_sha256 = "catalog-checksum"
        write_embedding_cache(
            self.root,
            self.matrix,
            ("A", "B"),
            _manifest_fields(self.catalog_sha256),
        )

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_cache_round_trip_validates_alignment_and_dtype(self) -> None:
        matrix, manifest = load_embedding_cache(
            self.root,
            expected_asins=("A", "B"),
            catalog_sha256=self.catalog_sha256,
            model_id="test-model",
        )

        self.assertEqual(matrix.dtype, np.float32)
        self.assertEqual(matrix.shape, (2, 2))
        self.assertEqual(manifest.dtype, "float16")

    def test_cache_rejects_wrong_asin_order(self) -> None:
        with self.assertRaisesRegex(ValueError, "ASIN order"):
            load_embedding_cache(
                self.root,
                expected_asins=("B", "A"),
                catalog_sha256=self.catalog_sha256,
                model_id="test-model",
            )

    def test_retriever_uses_fake_encoder_without_a_model_download(self) -> None:
        config = DenseConfig(
            name="dense_only",
            model_id="test-model",
            cache_directory=str(self.root),
            depth=1,
        )
        retriever = DenseRetriever(
            config,
            FakeEncoder([0.0, 1.0]),
            expected_asins=("A", "B"),
            catalog_sha256=self.catalog_sha256,
        )
        state = SessionState("session", {})
        state.record_turn(1, "blue shoes")

        result = retriever.retrieve("blue shoes", state.retrieval_view())

        self.assertEqual(result.candidate_ids, ("B",))
        self.assertEqual(result.model_revision, "abc123")

    def test_retriever_batches_and_fuses_multi_profile_queries(self) -> None:
        config = DenseConfig(
            name="hybrid_dense_profile",
            model_id="test-model",
            cache_directory=str(self.root),
            depth=2,
            query_mode="multi_profile",
        )
        encoder = FakeEncoder([0.0, 1.0])
        retriever = DenseRetriever(
            config,
            encoder,
            expected_asins=("A", "B"),
            catalog_sha256=self.catalog_sha256,
        )
        state = SessionState(
            "profile",
            {"preference_tags": ["comfort"], "summary": "Likes practical shoes."},
        )
        state.record_turn(1, "comfortable shoes")
        state.add_slot_value(
            "category", "shoes", turn=1, source_text="shoes", strength="hard"
        )

        result = retriever.retrieve(
            "comfortable shoes", state.retrieval_view(), "buying"
        )

        self.assertEqual(
            tuple(route.name for route in result.routes),
            ("identity", "scenario", "profile"),
        )
        self.assertEqual(len(encoder.texts), 3)
        self.assertEqual(set(result.candidate_ids), {"A", "B"})

    def test_retriever_uses_matching_fielded_indexes(self) -> None:
        directories: list[tuple[str, str]] = []
        matrices = {
            "identity": np.asarray([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32),
            "attributes": np.asarray([[0.0, 1.0], [1.0, 0.0]], dtype=np.float32),
            "needs": np.asarray([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32),
        }
        for view, matrix in matrices.items():
            directory = self.root / view
            fields = _manifest_fields(self.catalog_sha256)
            fields["document_version"] = FieldedDenseDocumentCompiler.VERSIONS[view]
            write_embedding_cache(directory, matrix, ("A", "B"), fields)
            directories.append((view, str(directory)))
        config = DenseConfig(
            name="hybrid_dense_fielded",
            model_id="test-model",
            query_mode="multi",
            view_cache_directories=tuple(directories),
            depth=2,
        )
        retriever = DenseRetriever(
            config,
            FakeEncoder([1.0, 0.0]),
            expected_asins=("A", "B"),
            catalog_sha256=self.catalog_sha256,
        )
        state = SessionState("fielded", {})
        state.record_turn(1, "waterproof boots")
        state.add_slot_value(
            "category", "boots", turn=1, source_text="boots", strength="hard"
        )
        state.add_slot_value(
            "feature", "waterproof", turn=1, source_text="waterproof"
        )

        result = retriever.retrieve(
            "waterproof boots", state.retrieval_view(), "buying"
        )
        by_name = {route.name: route.candidate_ids[0] for route in result.routes}

        self.assertEqual(by_name["identity"], "A")
        self.assertEqual(by_name["constraints"], "B")
        self.assertEqual(by_name["scenario"], "A")


if __name__ == "__main__":
    unittest.main()
