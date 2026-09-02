from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from starter.catalog import Product
from starter.catalog_cache import sha256_file
from starter.reranking import (
    RERANK_MANIFEST_FILE,
    RerankDocumentCompiler,
    RerankQueryCompiler,
    RerankerManifest,
    SemanticReranker,
    load_reranker_manifest,
    reranker_config,
)
from starter.retrieval import CandidateEvidence, RetrievalResult
from starter.state import SessionState


class FixedScorer:
    def __init__(self, scores) -> None:
        self.scores = scores
        self.pairs = []

    def score(self, pairs, *, batch_size: int):
        self.pairs = list(pairs)
        return self.scores


def _product(parent_asin: str, title: str) -> Product:
    return Product.from_source(
        {
            "parent_asin": parent_asin,
            "title": title,
            "categories": ["Clothing", "Women", "Shoes", "Boots"],
            "features": ["Comfortable"],
            "description": [],
            "details": {},
            "store": "Example",
        }
    )


def _retrieval(ids=("A", "B", "C", "D")) -> RetrievalResult:
    candidates = tuple(
        CandidateEvidence(
            parent_asin=parent_asin,
            fused_score=1.0 / rank,
            route_ranks={"current_message": rank},
            route_contributions={"current_message": 1.0 / rank},
            compatibility_score=1.0 if parent_asin == "A" else 0.0,
        )
        for rank, parent_asin in enumerate(ids, start=1)
    )
    return RetrievalResult(candidates, (), (), "multi_route_structured")


def _manifest() -> RerankerManifest:
    return RerankerManifest(
        model_id="test-model",
        model_revision="abc123",
        license="test",
        max_length=512,
        device="cpu",
        weight_file="model.safetensors",
        weight_sha256="checksum",
        library_versions={"test": "1"},
    )


def _state() -> SessionState:
    state = SessionState("session", {})
    state.record_turn(1, "I need black boots")
    return state


class RerankCompilerTest(unittest.TestCase):
    def test_query_compiler_excludes_replaced_and_no_preference_values(self) -> None:
        state = _state()
        state.add_slot_value("category", "Boots", turn=1, source_text="boots")
        state.add_slot_value("color", "Black", turn=1, source_text="black")
        state.record_turn(2, "Actually blue, any brand")
        state.replace_slot(
            "color", ("Blue",), turn=2, source_text="blue", new_revision=True
        )
        state.mark_no_preference(
            "brand", turn=2, source_text="any brand", clear_existing=False
        )

        query = RerankQueryCompiler().compile(
            "Actually blue, any brand", state.retrieval_view()
        )

        self.assertIn("Category: boots", query.text)
        self.assertIn("Color: blue", query.text)
        self.assertNotIn("black", query.text.casefold())
        self.assertNotIn("brand:", query.text.casefold())

    def test_document_compiler_uses_concise_product_fields(self) -> None:
        text = RerankDocumentCompiler().compile(_product("A", "Winter hiking boots"))

        self.assertIn("Title: Winter hiking boots", text)
        self.assertIn("Category: Clothing > Women > Shoes > Boots", text)
        self.assertIn("Features: Comfortable", text)

    def test_fielded_query_separates_required_and_preferred_values(self) -> None:
        state = _state()
        state.add_slot_value(
            "category", "Boots", turn=1, source_text="boots", strength="hard"
        )
        state.add_slot_value(
            "feature", "comfortable", turn=1, source_text="comfortable", strength="soft"
        )

        query = RerankQueryCompiler().compile(
            "comfortable boots", state.retrieval_view(), mode="fielded"
        )

        self.assertIn("Required: category: boots", query.text)
        self.assertIn("Preferred: feature: comfortable", query.text)
        self.assertEqual(query.version, "2")

    def test_fielded_document_places_structured_facts_before_description(self) -> None:
        product = Product.from_source(
            {
                "parent_asin": "A",
                "title": "Blue leather boots",
                "categories": ["Clothing", "Women", "Shoes", "Boots"],
                "features": ["Comfortable leather upper"],
                "description": ["For winter walking"],
                "details": {"Color": "Blue"},
                "price": 49.99,
                "store": "Example",
            }
        )

        text = RerankDocumentCompiler().compile(product, mode="fielded")

        self.assertIn("Product: Blue leather boots.", text)
        self.assertIn("Materials: leather.", text)
        self.assertIn("Colors: blue.", text)
        self.assertIn("Price: 49.99.", text)


class SemanticRerankerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.products = tuple(
            _product(parent_asin, f"Product {parent_asin}")
            for parent_asin in ("A", "B", "C", "D")
        )

    def test_legacy_safeguard_variants_do_not_enable_fielded_context(self) -> None:
        constraint = reranker_config("minilm_l4_constraint_legacy")
        bounded = reranker_config("minilm_l4_bounded")

        self.assertEqual(constraint.context_mode, "legacy")
        self.assertGreater(constraint.hard_contradiction_penalty, 0.0)
        self.assertEqual(bounded.context_mode, "legacy")
        self.assertEqual(bounded.max_rank_movement, 8)

    def test_semantic_variant_reranks_only_the_bounded_head(self) -> None:
        scorer = FixedScorer((0.1, 0.9, 0.5))
        reranker = SemanticReranker(
            self.products,
            reranker_config("minilm_l4_semantic", depth=3),
            scorer,
            _manifest(),
        )

        result = reranker.rerank(
            "winter boots", _state().retrieval_view(), _retrieval()
        )

        self.assertEqual(result.candidate_ids, ("B", "C", "A", "D"))
        self.assertEqual(result.depth, 3)
        self.assertEqual(len(scorer.pairs), 3)
        self.assertEqual(result.retrieval_result.candidates[-1].fused_score, 0.25)

    def test_equal_semantic_scores_keep_original_order(self) -> None:
        reranker = SemanticReranker(
            self.products,
            reranker_config("minilm_l4_semantic", depth=3),
            FixedScorer((1.0, 1.0, 1.0)),
            _manifest(),
        )

        result = reranker.rerank("boots", _state().retrieval_view(), _retrieval())

        self.assertEqual(result.candidate_ids, ("A", "B", "C", "D"))

    def test_blended_variant_preserves_retrieval_evidence(self) -> None:
        reranker = SemanticReranker(
            self.products,
            reranker_config(
                "minilm_l4_blended", depth=3, semantic_weight=0.25
            ),
            FixedScorer((0.1, 0.2, 0.9)),
            _manifest(),
        )

        result = reranker.rerank("boots", _state().retrieval_view(), _retrieval())
        first = result.retrieval_result.candidates[0]

        self.assertEqual(first.parent_asin, "A")
        self.assertEqual(first.route_ranks, {"current_message": 1})
        self.assertEqual(first.compatibility_score, 1.0)

    def test_malformed_scores_fail_before_changing_the_ranking(self) -> None:
        reranker = SemanticReranker(
            self.products,
            reranker_config("minilm_l4_blended", depth=3),
            FixedScorer((1.0, 2.0)),
            _manifest(),
        )

        with self.assertRaisesRegex(ValueError, "wrong number"):
            reranker.rerank("boots", _state().retrieval_view(), _retrieval())

    def test_per_call_config_changes_depth_without_mutating_default(self) -> None:
        scorer = FixedScorer((0.1, 0.9))
        default_config = reranker_config("minilm_l4_semantic", depth=3)
        reranker = SemanticReranker(
            self.products,
            default_config,
            scorer,
            _manifest(),
        )
        per_call = reranker_config("minilm_l4_semantic", depth=2)

        result = reranker.rerank(
            "boots", _state().retrieval_view(), _retrieval(), per_call
        )

        self.assertEqual(result.depth, 2)
        self.assertEqual(reranker.config, default_config)

    def test_constraint_variant_penalizes_a_hard_contradiction(self) -> None:
        state = _state()
        state.add_slot_value(
            "color", "black", turn=1, source_text="black", strength="hard"
        )
        retrieval = RetrievalResult(
            (
                CandidateEvidence(
                    "A", 1.0, {"current_message": 1}, {},
                    compatibility_score=-1.0,
                    contradicted_constraints=("color",),
                ),
                CandidateEvidence(
                    "B", 0.5, {"current_message": 2}, {},
                    compatibility_score=2.0,
                    matched_constraints=("color",),
                ),
            ),
            (),
            (),
            "multi_route_structured",
        )
        reranker = SemanticReranker(
            self.products,
            reranker_config("minilm_l4_constraint", depth=2),
            FixedScorer((0.9, 0.8)),
            _manifest(),
        )

        result = reranker.rerank(
            "black boots", state.retrieval_view(), retrieval
        )

        self.assertEqual(result.candidate_ids[:2], ("B", "A"))
        details = {item.parent_asin: item for item in result.candidates}
        self.assertGreater(details["A"].contradiction_penalty, 0.0)

    def test_guarded_variant_limits_rank_movement(self) -> None:
        config = replace(
            reranker_config("minilm_l4_guarded", depth=4),
            retrieval_weight=0.0,
            semantic_weight=1.0,
            compatibility_weight=0.0,
            hard_contradiction_penalty=0.0,
            max_rank_movement=1,
        )
        reranker = SemanticReranker(
            self.products,
            config,
            FixedScorer((0.1, 0.2, 0.3, 0.9)),
            _manifest(),
        )

        result = reranker.rerank("boots", _state().retrieval_view(), _retrieval())

        original = {parent_asin: rank for rank, parent_asin in enumerate(("A", "B", "C", "D"), 1)}
        for rank, parent_asin in enumerate(result.candidate_ids, 1):
            self.assertLessEqual(abs(rank - original[parent_asin]), 1)

    def test_route_aware_variant_uses_fielded_context_only_for_browsing(self) -> None:
        scorer = FixedScorer((0.4, 0.3, 0.2, 0.1))
        reranker = SemanticReranker(
            self.products,
            reranker_config("minilm_l4_route_aware", depth=4),
            scorer,
            _manifest(),
        )

        browsing = reranker.rerank(
            "boots", _state().retrieval_view(), _retrieval(), route="browsing"
        )
        browsing_document = scorer.pairs[0][1]
        buying = reranker.rerank(
            "boots", _state().retrieval_view(), _retrieval(), route="buying"
        )
        buying_document = scorer.pairs[0][1]

        self.assertEqual(browsing.context_mode, "fielded")
        self.assertEqual(browsing.query.version, "2")
        self.assertTrue(browsing_document.startswith("Product:"))
        self.assertEqual(buying.context_mode, "legacy")
        self.assertEqual(buying.query.version, "1")
        self.assertTrue(buying_document.startswith("Title:"))


class RerankerManifestTest(unittest.TestCase):
    def test_manifest_validates_model_and_weight_checksum(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            weight_path = root / "model.safetensors"
            weight_path.write_bytes(b"model")
            manifest = {
                "model_id": "test-model",
                "model_revision": "abc123",
                "license": "test",
                "max_length": 512,
                "device": "cpu",
                "weight_file": weight_path.name,
                "weight_sha256": sha256_file(weight_path),
                "library_versions": {"test": "1"},
            }
            (root / RERANK_MANIFEST_FILE).write_text(
                json.dumps(manifest), encoding="utf-8"
            )

            loaded = load_reranker_manifest(root, "test-model")

            self.assertEqual(loaded.model_revision, "abc123")
            with self.assertRaisesRegex(ValueError, "model ID"):
                load_reranker_manifest(root, "other-model")


if __name__ == "__main__":
    unittest.main()
