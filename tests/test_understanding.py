from __future__ import annotations

import unittest

from starter.memory import MemoryUpdater
from starter.state import SessionStore
from starter.understanding import (
    CatalogVocabularyBuilder,
    UnderstandingEngine,
)


def _product(title: str, categories: list[str], store: str) -> dict:
    return {
        "parent_asin": title,
        "title": title,
        "categories": categories,
        "store": store,
        "details": {"Brand": store},
    }


def _vocabulary():
    builder = CatalogVocabularyBuilder()
    products = (
        _product(
            "Women slippers",
            ["Clothing, Shoes & Jewelry", "Women", "Shoes", "Slippers"],
            "Clarks",
        ),
        _product(
            "Men slippers",
            ["Clothing, Shoes & Jewelry", "Men", "Shoes", "Slippers"],
            "Lulex",
        ),
        _product(
            "Men running shoes",
            ["Clothing, Shoes & Jewelry", "Men", "Shoes", "Athletic", "Running"],
            "Nike",
        ),
        _product(
            "Women dresses",
            ["Clothing, Shoes & Jewelry", "Women", "Clothing", "Dresses"],
            "Example Fashion",
        ),
        _product(
            "Women boots",
            ["Clothing, Shoes & Jewelry", "Women", "Shoes", "Boots"],
            "Clarks",
        ),
    )
    for product in products:
        builder.observe(product)
    return builder.build()


class UnderstandingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = UnderstandingEngine(_vocabulary())
        self.updater = MemoryUpdater()
        self.store = SessionStore()

    def _understand(self, message: str):
        state = self.store.reset("session", {"preference_tags": []})
        state.record_turn(1, message)
        return self.engine.understand(message, state.retrieval_view())

    @staticmethod
    def _updates(understanding, slot_name: str, action: str = "add"):
        return [
            update
            for update in understanding.parsed_turn.slot_updates
            if update.slot_name == slot_name and update.action == action
        ]

    def test_reworded_category_queries_use_the_same_catalog_path(self) -> None:
        messages = (
            "I need women's slippers.",
            "I'm looking for slippers for women.",
            "Show me house shoes for women.",
        )
        paths = []
        for message in messages:
            understanding = self._understand(message)
            paths.append(self._updates(understanding, "category")[0].values[0])

        self.assertEqual(len(set(paths)), 1)
        self.assertEqual(
            paths[0],
            "Clothing, Shoes & Jewelry > Women > Shoes > Slippers",
        )

    def test_structured_slots_are_extracted(self) -> None:
        understanding = self._understand(
            "I need Clarks women's grey leather slippers in size 8 under $40."
        )

        self.assertEqual(self._updates(understanding, "audience")[0].values, ("women",))
        self.assertEqual(self._updates(understanding, "color")[0].values, ("gray",))
        self.assertEqual(self._updates(understanding, "material")[0].values, ("leather",))
        self.assertEqual(self._updates(understanding, "size")[0].values, ("8",))
        self.assertEqual(self._updates(understanding, "max_price")[0].values, (40.0,))
        self.assertEqual(self._updates(understanding, "brand")[0].values, ("Clarks",))

    def test_rare_brand_requires_an_explicit_brand_cue(self) -> None:
        implicit = self._understand("I need Lulex men's slippers.")
        explicit = self._understand("I need men's slippers from brand Lulex.")

        self.assertEqual(self._updates(implicit, "brand"), [])
        self.assertEqual(self._updates(explicit, "brand")[0].values, ("Lulex",))

    def test_buying_and_browsing_routes_have_reasons(self) -> None:
        cases = (
            ("I need leather slippers under $40.", "buying"),
            ("I'm looking for women's shoes, but I'm still exploring.", "browsing"),
            ("Show me ideas for a beach holiday.", "browsing"),
        )
        for message, expected_route in cases:
            with self.subTest(message=message):
                decision = self._understand(message).intent
                self.assertEqual(decision.route, expected_route)
                self.assertTrue(decision.reasons)
                self.assertGreaterEqual(decision.confidence, 0.5)

    def test_boundary_responses_are_separate_events(self) -> None:
        cases = (
            (
                "I don't have a preference for material; please use your judgment.",
                "no_preference",
                True,
            ),
            (
                "I don't have an additional preference for material.",
                "no_additional_preference",
                False,
            ),
        )
        for message, event_type, clear_existing in cases:
            with self.subTest(message=message):
                event = self._understand(message).parsed_turn.events[0]
                self.assertEqual(event.event_type, event_type)
                self.assertEqual(event.attribute, "material")
                self.assertEqual(event.clear_existing, clear_existing)

    def test_targeted_correction_deactivates_only_the_old_value(self) -> None:
        understanding = self._understand("Not black anymore; blue is fine.")

        self.assertEqual(
            self._updates(understanding, "color", "deactivate")[0].values,
            ("black",),
        )
        self.assertEqual(self._updates(understanding, "color")[0].values, ("blue",))
        self.assertEqual(
            understanding.parsed_turn.events[0].event_type,
            "intent_override",
        )

    def test_generic_override_removes_soft_state_and_keeps_hard_state(self) -> None:
        state = self.store.reset("override", {"preference_tags": []})
        state.record_turn(1, "I need shirts. Comfort would be nice, and blue is required.")
        state.add_slot_value(
            "category", "shirts", turn=1, source_text="shirts", strength="hard"
        )
        state.add_slot_value(
            "feature", "comfort", turn=1, source_text="comfort", strength="soft"
        )
        state.add_slot_value(
            "color", "blue", turn=1, source_text="blue", strength="hard"
        )
        state.record_turn(
            2,
            "Actually, ignore my earlier preference. What I need is: cotton.",
        )
        understanding = self.engine.understand(
            state.messages[-1].text,
            state.retrieval_view(),
        )

        actions = self.updater.apply(state, understanding)

        self.assertEqual(
            state.active_constraints(),
            {
                "category": ("shirts",),
                "color": ("blue",),
                "material": ("cotton",),
            },
        )
        self.assertEqual(state.search_revision, 2)
        self.assertIn("deactivate_soft:feature", actions)

    def test_category_override_replaces_audience_and_dependent_size(self) -> None:
        state = self.store.reset("category", {"preference_tags": []})
        first = "I need women's slippers in size 8."
        state.record_turn(1, first)
        self.updater.apply(
            state,
            self.engine.understand(first, state.retrieval_view()),
        )

        second = "Actually, I need men's running shoes."
        state.record_turn(2, second)
        self.updater.apply(
            state,
            self.engine.understand(second, state.retrieval_view()),
        )

        constraints = state.active_constraints()
        self.assertEqual(constraints["audience"], ("men",))
        self.assertNotIn("size", constraints)
        self.assertIn("men shoes athletic running", constraints["category"][0])
        self.assertEqual(state.search_revision, 2)

    def test_evaluator_constraint_phrase_is_preserved_as_feature(self) -> None:
        understanding = self._understand(
            "For that, what matters is: moisture-wicking fabric; zippered pockets."
        )
        features = self._updates(understanding, "feature")
        values = tuple(value for update in features for value in update.values)
        self.assertIn("moisture-wicking fabric", values)
        self.assertIn("zippered pockets", values)

    def test_non_latin_only_constraint_fragment_is_ignored_safely(self) -> None:
        state = self.store.reset("unicode", {"preference_tags": []})
        message = "For that, what matters is: PU; 进口."
        state.record_turn(1, message)

        understanding = self.engine.understand(message, state.retrieval_view())
        self.updater.apply(state, understanding)

        self.assertEqual(state.active_constraints()["feature"], ("pu",))

    def test_profile_tags_are_weak_priors_not_explicit_slots(self) -> None:
        state = self.store.reset(
            "profile",
            {"preference_tags": ["comfort", "fit", "comfort"]},
        )
        message = "I'm still exploring."
        state.record_turn(1, message)
        understanding = self.engine.understand(message, state.retrieval_view())

        self.assertEqual(
            tuple(prior.value for prior in understanding.profile_priors),
            ("comfort", "fit"),
        )
        self.assertTrue(all(prior.confidence == 0.2 for prior in understanding.profile_priors))
        self.assertEqual(state.active_constraints(), {})


if __name__ == "__main__":
    unittest.main()
