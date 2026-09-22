from __future__ import annotations

import unittest

from starter.intent import IntentParse, ObservedClaim, parse_intent


class ParseIntentTest(unittest.TestCase):
    def test_buying_initial_message(self) -> None:
        result = parse_intent(
            "I'm looking for hiking shoes. A key requirement is: waterproof."
        )

        self.assertEqual(result, IntentParse((
            ObservedClaim("category", "hiking shoes", "required"),
            ObservedClaim("feature", "waterproof", "required"),
        )))

    def test_browsing_initial_message(self) -> None:
        result = parse_intent("I'm looking for summer dresses, but I'm still exploring.")

        self.assertEqual(result, IntentParse((
            ObservedClaim("category", "summer dresses", "required"),
        )))

    def test_intent_override_initial_message(self) -> None:
        result = parse_intent("I'm looking for handbags. leather")

        self.assertEqual(result, IntentParse((
            ObservedClaim("category", "handbags", "required"),
            ObservedClaim("material", "leather", "preferred"),
        )))

    def test_attribute_information_reply(self) -> None:
        result = parse_intent(
            "For that, what matters is: waterproof; outdoor use.",
            ask_attribute="feature",
        )

        self.assertEqual(result, IntentParse((
            ObservedClaim("feature", "waterproof; outdoor use", "preferred"),
        )))

    def test_no_preference_replies(self) -> None:
        messages = (
            "I don't have a preference for color; please use your judgment.",
            "I don't have an additional preference for color.",
        )

        for message in messages:
            with self.subTest(message=message):
                self.assertEqual(
                    parse_intent(message, ask_attribute="color"),
                    IntentParse((ObservedClaim("color", None, "indifferent"),)),
                )

    def test_override_returns_required_matching_attribute_claim(self) -> None:
        result = parse_intent(
            "Actually, ignore my earlier preference. What I need is: nylon."
        )

        self.assertEqual(
            result,
            IntentParse((ObservedClaim("material", "nylon", "required"),)),
        )

    def test_bare_linked_reply(self) -> None:
        self.assertEqual(
            parse_intent("navy", ask_attribute="color"),
            IntentParse((ObservedClaim("color", "navy", "preferred"),)),
        )

    def test_unknown_unlinked_message(self) -> None:
        self.assertEqual(
            parse_intent("Show me something different."),
            IntentParse((), unresolved=True),
        )


if __name__ == "__main__":
    unittest.main()
