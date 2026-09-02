from __future__ import annotations

import unittest

from starter.state import SessionState, SessionStore


class SessionStateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.store = SessionStore()
        self.state = self.store.reset("session-a", {"preference_tags": ["comfort"]})
        self.state.record_turn(1, "I am looking for something comfortable.")

    def test_session_store_isolates_sessions_and_copies_profiles(self) -> None:
        original_profile = {"preference_tags": ["style"]}
        other = self.store.reset("session-b", original_profile)
        original_profile["preference_tags"].append("changed outside")

        self.state.add_slot_value(
            "color", "Black", turn=1, source_text="black", strength="hard"
        )

        self.assertEqual(other.user_profile["preference_tags"], ["style"])
        self.assertEqual(other.active_constraints(), {})
        self.assertIs(self.store.get("session-a"), self.state)
        with self.assertRaisesRegex(RuntimeError, "was not initialized"):
            self.store.get("missing")

        self.store.remove("session-b")
        with self.assertRaises(RuntimeError):
            self.store.get("session-b")

    def test_turns_must_be_contiguous_and_within_limit(self) -> None:
        invalid_calls = (
            (1, "duplicate"),
            (3, "skipped turn"),
            (0, "too small"),
            (11, "too large"),
        )
        for turn, message in invalid_calls:
            with self.subTest(turn=turn):
                with self.assertRaises(ValueError):
                    self.state.record_turn(turn, message)

        self.state.record_turn(2, "This is the second turn.")
        self.assertEqual(self.state.current_turn, 2)
        self.assertEqual([message.turn for message in self.state.messages], [1, 2])

    def test_values_accumulate_inside_grouped_slots(self) -> None:
        self.state.add_slot_value(
            "category", "Slippers", turn=1, source_text="slippers", strength="hard"
        )
        self.state.add_slot_value(
            "feature",
            "Waterproof",
            turn=1,
            source_text="waterproof and lightweight",
            match_mode="all",
        )
        self.state.add_slot_value(
            "feature",
            "Lightweight",
            turn=1,
            source_text="waterproof and lightweight",
            match_mode="all",
        )

        self.assertEqual(
            self.state.active_constraints(),
            {"category": ("slippers",), "feature": ("waterproof", "lightweight")},
        )
        self.assertEqual(self.state.slots["feature"].match_mode, "all")

    def test_one_grouped_value_can_be_deactivated(self) -> None:
        for color in ("Black", "Blue", "Red"):
            self.state.add_slot_value(
                "color", color, turn=1, source_text="black, blue, or red"
            )

        self.state.deactivate_slot_value(
            "color",
            "black",
            turn=1,
            reason="user_override",
            new_revision=True,
        )

        self.assertEqual(self.state.active_constraints()["color"], ("blue", "red"))
        black = self.state.slots["color"].values[0]
        self.assertFalse(black.active)
        self.assertEqual(black.deactivated_turn, 1)
        self.assertEqual(black.deactivation_reason, "user_override")
        self.assertEqual(self.state.search_revision, 2)

    def test_replacing_a_slot_preserves_inactive_history(self) -> None:
        self.state.add_slot_value(
            "color", "Black", turn=1, source_text="black", strength="hard"
        )
        self.state.record_turn(2, "Actually, green or navy is fine.")
        self.state.replace_slot(
            "color",
            ("Green", "Navy"),
            turn=2,
            source_text="green or navy",
            strength="hard",
            match_mode="any",
            new_revision=True,
        )

        color_slot = self.state.slots["color"]
        self.assertEqual(self.state.active_constraints()["color"], ("green", "navy"))
        self.assertEqual(len(color_slot.values), 3)
        self.assertFalse(color_slot.values[0].active)
        self.assertEqual(color_slot.values[0].deactivation_reason, "replaced")

    def test_no_additional_preference_preserves_existing_value(self) -> None:
        self.state.add_slot_value(
            "material", "Leather", turn=1, source_text="leather", strength="hard"
        )
        self.state.mark_no_preference(
            "material",
            turn=1,
            source_text="I have no additional material preference.",
            clear_existing=False,
        )

        self.assertEqual(self.state.active_constraints()["material"], ("leather",))
        self.assertEqual(self.state.no_preference_attributes(), ("material",))

        self.state.record_turn(2, "Cotton would also work.")
        self.state.add_slot_value(
            "material", "Cotton", turn=2, source_text="cotton would also work"
        )
        self.assertEqual(self.state.no_preference_attributes(), ())
        self.assertEqual(self.state.active_constraints()["material"], ("leather", "cotton"))

    def test_no_preference_can_clear_an_existing_constraint(self) -> None:
        self.state.add_slot_value("color", "Black", turn=1, source_text="black")
        self.state.mark_no_preference(
            "color",
            turn=1,
            source_text="Color no longer matters.",
            clear_existing=True,
        )

        self.assertNotIn("color", self.state.active_constraints())
        self.assertEqual(self.state.no_preference_attributes(), ("color",))
        self.assertEqual(
            self.state.slots["color"].values[0].deactivation_reason,
            "no_preference",
        )

    def test_category_override_invalidates_only_named_dependencies(self) -> None:
        self.state.add_slot_value(
            "category", "Running Shoes", turn=1, source_text="running shoes"
        )
        self.state.add_slot_value("size", "8", turn=1, source_text="size 8")
        self.state.add_slot_value("color", "Black", turn=1, source_text="black")
        self.state.cache_derived("candidate_ids", ["A", "B"])
        self.state.record_turn(2, "Actually, I need hiking boots.")

        self.state.replace_category(
            "Hiking Boots",
            turn=2,
            source_text="I need hiking boots",
            invalidate_slots=("size",),
        )

        self.assertEqual(
            self.state.active_constraints(),
            {"category": ("hiking boots",), "color": ("black",)},
        )
        self.assertEqual(self.state.search_revision, 2)
        self.assertEqual(self.state.get_cached("candidate_ids"), None)
        self.assertFalse(self.state.slots["category"].values[0].active)
        self.assertFalse(self.state.slots["size"].values[0].active)

    def test_full_restart_retains_audit_history_and_profile(self) -> None:
        self.state.add_slot_value("color", "Black", turn=1, source_text="black")
        self.state.mark_no_preference(
            "material", turn=1, source_text="no preference", clear_existing=False
        )
        self.state.record_shown_products(turn=1, ranked_ids=("A", "B"))
        self.state.record_turn(2, "Forget all that and start over.")

        self.state.full_restart(turn=2)

        self.assertEqual(self.state.active_constraints(), {})
        self.assertEqual(self.state.no_preference_attributes(), ())
        self.assertEqual(self.state.current_revision_shown_ids(), ())
        self.assertEqual(self.state.search_revision, 2)
        self.assertEqual(self.state.user_profile["preference_tags"], ["comfort"])
        self.assertEqual(len(self.state.messages), 2)
        self.assertEqual(len(self.state.shown_products), 2)

    def test_context_changes_clear_derived_cache(self) -> None:
        version_after_message = self.state.context_version
        self.state.cache_derived("query", "comfortable")

        self.state.add_slot_value(
            "feature", "Comfortable", turn=1, source_text="comfortable"
        )

        self.assertGreater(self.state.context_version, version_after_message)
        self.assertIsNone(self.state.get_cached("query"))

    def test_shown_products_are_tracked_per_revision(self) -> None:
        self.state.record_shown_products(turn=1, ranked_ids=("A", "B"))
        self.state.record_turn(2, "Show me something different.")
        self.state.record_shown_products(turn=2, ranked_ids=("B", "A"))

        shown_b = self.state.shown_products[(1, "B")]
        self.assertEqual(shown_b.first_turn, 1)
        self.assertEqual(shown_b.last_turn, 2)
        self.assertEqual(shown_b.best_rank, 1)
        self.assertEqual(shown_b.display_count, 2)

        self.state.start_new_search_revision(turn=2, reason="intent_override")
        self.assertEqual(self.state.current_revision_shown_ids(), ())
        self.state.record_shown_products(turn=2, ranked_ids=("A",))
        self.assertEqual(self.state.current_revision_shown_ids(), ("A",))
        self.assertIn((1, "A"), self.state.shown_products)
        self.assertIn((2, "A"), self.state.shown_products)

    def test_clarification_history_is_unique_and_revision_scoped(self) -> None:
        self.state.record_clarification(turn=1, attribute="material")
        self.state.record_clarification(turn=1, attribute="material")

        self.assertEqual(self.state.current_revision_asked_attributes(), ("material",))
        self.state.start_new_search_revision(turn=1, reason="intent_override")
        self.assertEqual(self.state.current_revision_asked_attributes(), ())
        self.assertEqual(len(self.state.clarification_history), 1)

    def test_retrieval_view_is_a_detached_read_only_summary(self) -> None:
        self.state.add_slot_value("color", "Black", turn=1, source_text="black")
        view = self.state.retrieval_view()

        self.assertEqual(view.active_constraints, {"color": ("black",)})
        self.assertEqual(view.active_slots["color"].match_mode, "any")
        self.assertEqual(view.active_slots["color"].values[0].confidence, 1.0)
        with self.assertRaises(TypeError):
            view.active_constraints["color"] = ("blue",)

        view.user_profile["preference_tags"].append("changed in view")
        self.assertEqual(self.state.user_profile["preference_tags"], ["comfort"])


if __name__ == "__main__":
    unittest.main()
