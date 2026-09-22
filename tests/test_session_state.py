from __future__ import annotations

import unittest

from starter.intent import ObservedClaim
from starter.session_state import SessionState, SessionStateStore, TurnRecord


class SessionStateStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.store = SessionStateStore()
        self.store.reset("session")

    def test_question_reply_and_accumulated_claims(self) -> None:
        first_message = "I'm looking for hiking shoes, but I'm still exploring."
        self.store.receive("session", 1, first_message)
        self.store.record_ask_attribute("session", "material")

        state = self.store.receive("session", 2, "nylon")
        state = self.store.receive("session", 3, first_message)

        self.assertEqual(
            state.turns,
            (
                TurnRecord(1, first_message, None, False),
                TurnRecord(2, "nylon", "material", False),
                TurnRecord(3, first_message, None, False),
            ),
        )
        self.assertEqual(
            state.active_claims,
            (
                ObservedClaim("category", "hiking shoes", "required"),
                ObservedClaim("material", "nylon", "preferred"),
            ),
        )
        self.assertIsNone(state.pending_ask_attribute)

    def test_indifference_replaces_claims_for_that_attribute(self) -> None:
        self.store.receive("session", 1, "I'm looking for handbags. leather")
        self.store.record_ask_attribute("session", "material")

        state = self.store.receive(
            "session",
            2,
            "I don't have a preference for material; please use your judgment.",
        )

        self.assertEqual(
            state.active_claims,
            (
                ObservedClaim("category", "handbags", "required"),
                ObservedClaim("material", None, "indifferent"),
            ),
        )

    def test_new_claim_replaces_only_its_matching_attribute(self) -> None:
        self.store.receive("session", 1, "I'm looking for handbags. leather")
        self.store.record_ask_attribute("session", "material")

        state = self.store.receive("session", 2, "nylon")

        self.assertEqual(
            state.active_claims,
            (
                ObservedClaim("category", "handbags", "required"),
                ObservedClaim("material", "nylon", "preferred"),
            ),
        )

    def test_override_replaces_matching_attribute_only(self) -> None:
        self.store.receive("session", 1, "I'm looking for handbags. leather")
        self.store.record_ask_attribute("session", "color")
        self.store.receive("session", 2, "blue")

        state = self.store.receive(
            "session",
            3,
            "Actually, ignore my earlier preference. What I need is: nylon.",
        )

        self.assertEqual(
            state.active_claims,
            (
                ObservedClaim("category", "handbags", "required"),
                ObservedClaim("material", "nylon", "required"),
                ObservedClaim("color", "blue", "preferred"),
            ),
        )

    def test_unresolved_message_preserves_active_intent(self) -> None:
        self.store.receive("session", 1, "I'm looking for shoes, but I'm still exploring.")
        previous_claims = self.store.get("session").active_claims

        state = self.store.receive("session", 2, "Show me something different.")

        unresolved = TurnRecord(2, "Show me something different.", None, True)
        self.assertEqual(state.active_claims, previous_claims)
        self.assertEqual(state.turns[-1], unresolved)
        self.assertEqual(state.unresolved_turns, (unresolved,))

    def test_sessions_are_isolated_and_reset_clears_one(self) -> None:
        self.store.reset("other")
        self.store.receive("session", 1, "I'm looking for shoes, but I'm still exploring.")
        other_state = self.store.receive(
            "other",
            1,
            "I'm looking for hats, but I'm still exploring.",
        )

        self.assertEqual(self.store.reset("session"), SessionState())
        self.assertEqual(self.store.get("other"), other_state)


if __name__ == "__main__":
    unittest.main()
