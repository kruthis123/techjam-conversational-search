from __future__ import annotations

import sqlite3
import unittest

from starter.catalog import Product
from starter.retrieval import (
    LexicalRetriever,
    QueryCompiler,
    RouteResult,
    reciprocal_rank_fusion,
    retrieval_config,
)
from starter.state import SessionState


def _product(
    parent_asin: str,
    title: str,
    *,
    material: str = "",
    color: str = "",
    price: float | None = None,
) -> Product:
    features = [value for value in (material, color, "comfortable") if value]
    return Product.from_source(
        {
            "parent_asin": parent_asin,
            "title": title,
            "categories": ["Clothing, Shoes & Jewelry", "Women", "Shoes", "Slippers"],
            "features": features,
            "details": {},
            "description": [],
            "store": "Example",
            "price": price,
        }
    )


def _connection(products: tuple[Product, ...]) -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.execute(
        "CREATE VIRTUAL TABLE products USING fts5("
        "parent_asin UNINDEXED, title, categories, features, details, store, description)"
    )
    connection.executemany(
        "INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            (
                product.parent_asin,
                product.title,
                product.categories_text,
                product.features_text,
                product.details_text,
                product.store,
                product.description_text,
            )
            for product in products
        ],
    )
    return connection


def _state() -> SessionState:
    state = SessionState("session", {})
    state.record_turn(1, "I need women's slippers")
    state.add_slot_value(
        "category",
        "clothing shoes jewelry women shoes slippers",
        turn=1,
        source_text="women's slippers",
        strength="hard",
    )
    return state


class QueryCompilerTest(unittest.TestCase):
    def test_compiler_uses_active_state_and_excludes_overridden_values(self) -> None:
        state = _state()
        state.add_slot_value("color", "black", turn=1, source_text="black")
        state.record_turn(2, "Actually, blue instead of black")
        state.deactivate_slot_value("color", "black", turn=2)
        state.add_slot_value("color", "blue", turn=2, source_text="blue")

        queries = QueryCompiler().compile(state.messages[-1].text, state.retrieval_view())
        by_name = {query.name: query for query in queries}

        self.assertIn("blue", by_name["complete_state"].terms)
        self.assertNotIn("black", by_name["complete_state"].terms)
        self.assertEqual(by_name["latest_constraint"].terms, ("blue",))

    def test_compiler_emits_field_specific_routes(self) -> None:
        state = _state()
        queries = QueryCompiler().compile("comfortable slippers", state.retrieval_view())
        by_name = {query.name: query for query in queries}

        self.assertGreater(
            by_name["title_heavy"].field_weights[1],
            by_name["feature_heavy"].field_weights[1],
        )
        self.assertGreater(
            by_name["feature_heavy"].field_weights[3],
            by_name["title_heavy"].field_weights[3],
        )


class FusionTest(unittest.TestCase):
    def test_rrf_rewards_candidates_supported_by_multiple_routes(self) -> None:
        routes = (
            RouteResult("one", ("A", "B"), (-2.0, -1.0)),
            RouteResult("two", ("B", "C"), (-3.0, -1.0)),
        )

        fused = reciprocal_rank_fusion(routes, {"one": 1.0, "two": 1.0}, 60)

        self.assertGreater(fused["B"][0], fused["A"][0])
        self.assertEqual(fused["B"][1], {"one": 2, "two": 1})
        self.assertEqual(set(fused["B"][2]), {"one", "two"})


class LexicalRetrieverTest(unittest.TestCase):
    def setUp(self) -> None:
        self.products = (
            _product("A", "Black leather slippers", material="leather", color="black", price=40),
            _product("B", "Blue fabric slippers", material="polyester", color="blue", price=30),
            _product("C", "Minimal slippers", price=None),
        )
        self.connection = _connection(self.products)

    def tearDown(self) -> None:
        self.connection.close()

    def test_multi_route_result_contains_route_evidence_and_stable_ids(self) -> None:
        state = _state()
        state.add_slot_value(
            "material", "leather", turn=1, source_text="leather", strength="hard"
        )
        retriever = LexicalRetriever(
            self.connection,
            self.products,
            retrieval_config("multi_route_structured"),
        )

        result = retriever.retrieve("leather slippers", state.retrieval_view(), "buying")

        self.assertEqual(result.candidate_ids[0], "A")
        self.assertIn("structured", {route.name for route in result.routes})
        self.assertIn("material", result.candidates[0].matched_constraints)
        self.assertTrue(result.candidates[0].route_ranks)

    def test_missing_metadata_is_unknown_not_a_contradiction(self) -> None:
        state = _state()
        state.add_slot_value(
            "material", "leather", turn=1, source_text="leather", strength="hard"
        )
        retriever = LexicalRetriever(
            self.connection,
            self.products,
            retrieval_config("multi_route_structured"),
        )

        _, _, contradictions = retriever.structured_scorer.score("C", state.retrieval_view())

        self.assertNotIn("material", contradictions)

    def test_grouped_all_slot_requires_every_known_value(self) -> None:
        state = _state()
        state.add_slot_value(
            "material", "leather", turn=1, source_text="leather", match_mode="all"
        )
        state.add_slot_value(
            "material", "cotton", turn=1, source_text="cotton", match_mode="all"
        )
        retriever = LexicalRetriever(
            self.connection,
            self.products,
            retrieval_config("multi_route_structured"),
        )

        _, matches, contradictions = retriever.structured_scorer.score(
            "A", state.retrieval_view()
        )

        self.assertNotIn("material", matches)
        self.assertIn("material", contradictions)

    def test_buying_and_browsing_use_different_route_contributions(self) -> None:
        state = _state().retrieval_view()
        retriever = LexicalRetriever(
            self.connection,
            self.products,
            retrieval_config("multi_route_rrf"),
        )

        buying = retriever.retrieve("comfortable slippers", state, "buying")
        browsing = retriever.retrieve("comfortable slippers", state, "browsing")
        buying_current = buying.candidates[0].route_contributions["current_message"]
        browsing_current = browsing.candidates[0].route_contributions["current_message"]

        self.assertGreater(browsing_current, buying_current)

    def test_single_bm25_fallback_uses_only_the_current_message_route(self) -> None:
        retriever = LexicalRetriever(
            self.connection,
            self.products,
            retrieval_config("multi_route_structured"),
        )

        result = retriever.fallback("leather slippers", _state().retrieval_view(), "buying")

        self.assertEqual(tuple(route.name for route in result.routes), ("current_message",))
        self.assertEqual(result.config_name, "single_bm25")

    def test_per_call_route_overrides_do_not_mutate_retriever(self) -> None:
        retriever = LexicalRetriever(
            self.connection,
            self.products,
            retrieval_config("multi_route_structured"),
        )
        original_config = retriever.config

        result = retriever.retrieve(
            "leather slippers",
            _state().retrieval_view(),
            "buying",
            route_weights={"current_message": 2.0},
            enabled_routes=("current_message",),
        )

        self.assertEqual(tuple(route.name for route in result.routes), ("current_message",))
        self.assertEqual(retriever.config, original_config)
        self.assertEqual(
            result.candidates[0].route_contributions["current_message"],
            round(2.0 / 61.0, 8),
        )

    def test_negative_per_call_route_weight_is_rejected(self) -> None:
        retriever = LexicalRetriever(
            self.connection,
            self.products,
            retrieval_config("multi_route_structured"),
        )

        with self.assertRaisesRegex(ValueError, "must not be negative"):
            retriever.retrieve(
                "leather slippers",
                _state().retrieval_view(),
                "buying",
                route_weights={"current_message": -1.0},
            )


if __name__ == "__main__":
    unittest.main()
