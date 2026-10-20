from __future__ import annotations

from copy import deepcopy
import unittest

from starter.constraint_comparison import (
    assess_budget_ceiling,
    assess_candidate_constraints,
    assess_observed_text_constraint,
)
from starter.eligibility import AssessmentState, EligibilityStatus
from starter.fusion import FusedCandidate, RouteEvidence
from starter.intent import ObservedClaim


class AssessObservedTextConstraintTest(unittest.TestCase):
    def test_confirms_complete_sequence_with_case_and_punctuation_changes(self) -> None:
        record = {
            "parent_asin": "PRODUCT",
            "features": ["Lightweight WATER-resistant shell for travel."],
        }
        claim = ObservedClaim("feature", "water resistant shell", "required")

        assessment = assess_observed_text_constraint(record, claim)

        self.assertEqual(assessment.state, AssessmentState.CONFIRMED_MATCH)
        self.assertEqual(assessment.attribute, "feature")
        self.assertIn("features", assessment.reason)

    def test_does_not_match_tokens_inside_a_longer_word(self) -> None:
        record = {"parent_asin": "PRODUCT", "title": "Infrared running jacket"}
        claim = ObservedClaim("color", "red", "required")

        assessment = assess_observed_text_constraint(record, claim)

        self.assertEqual(assessment.state, AssessmentState.UNKNOWN)

    def test_returns_unknown_when_sequence_is_absent(self) -> None:
        record = {
            "parent_asin": "PRODUCT",
            "title": "Cotton crew neck shirt",
            "description": ["Soft everyday layer."],
        }
        claim = ObservedClaim("feature", "water resistant", "required")

        assessment = assess_observed_text_constraint(record, claim)

        self.assertEqual(assessment.state, AssessmentState.UNKNOWN)
        self.assertNotEqual(
            assessment.state,
            AssessmentState.CONFIRMED_CONTRADICTION,
        )

    def test_returns_unresolved_when_claim_has_no_value(self) -> None:
        record = {"parent_asin": "PRODUCT", "title": "Cotton shirt"}
        claim = ObservedClaim("material", None, "required")

        assessment = assess_observed_text_constraint(record, claim)

        self.assertEqual(assessment.state, AssessmentState.UNRESOLVED)

    def test_preserves_raw_catalog_record(self) -> None:
        record = {
            "parent_asin": "PRODUCT",
            "title": "Travel jacket",
            "features": ["Water resistant", None],
            "details": {"care": {"method": "Machine wash"}},
        }
        original = deepcopy(record)
        claim = ObservedClaim("feature", "water resistant", "required")

        assess_observed_text_constraint(record, claim)

        self.assertEqual(record, original)


class AssessBudgetCeilingTest(unittest.TestCase):
    def test_price_below_strict_ceiling_is_confirmed(self) -> None:
        assessment = assess_budget_ceiling(
            {"parent_asin": "PRODUCT", "price": 79.99},
            ObservedClaim("budget", "under $80", "required"),
        )

        self.assertEqual(assessment.state, AssessmentState.CONFIRMED_MATCH)
        self.assertEqual(assessment.attribute, "budget")
        self.assertIn("price", assessment.reason)
        self.assertIn("79.99", assessment.reason)
        self.assertIn("80.0", assessment.reason)

    def test_price_equal_to_or_above_strict_ceiling_is_contradicted(self) -> None:
        for price in (80, 81):
            with self.subTest(price=price):
                assessment = assess_budget_ceiling(
                    {"parent_asin": "PRODUCT", "price": price},
                    ObservedClaim("budget", "under 80", "required"),
                )

                self.assertEqual(
                    assessment.state,
                    AssessmentState.CONFIRMED_CONTRADICTION,
                )

    def test_price_equal_to_inclusive_ceiling_is_confirmed(self) -> None:
        for wording in ("up to $80", "<= 80"):
            with self.subTest(wording=wording):
                assessment = assess_budget_ceiling(
                    {"parent_asin": "PRODUCT", "price": 80},
                    ObservedClaim("budget", wording, "required"),
                )

                self.assertEqual(
                    assessment.state,
                    AssessmentState.CONFIRMED_MATCH,
                )

    def test_missing_or_unsupported_catalog_price_is_unknown(self) -> None:
        records = (
            {"parent_asin": "PRODUCT"},
            {"parent_asin": "PRODUCT", "price": None},
            {"parent_asin": "PRODUCT", "price": "79.99"},
            {"parent_asin": "PRODUCT", "price": True},
        )

        for record in records:
            with self.subTest(record=record):
                assessment = assess_budget_ceiling(
                    record,
                    ObservedClaim("budget", "up to 80", "required"),
                )

                self.assertEqual(assessment.state, AssessmentState.UNKNOWN)

    def test_unsupported_budget_wording_is_unresolved(self) -> None:
        assessment = assess_budget_ceiling(
            {"parent_asin": "PRODUCT", "price": 75},
            ObservedClaim("budget", "budget around $80", "required"),
        )

        self.assertEqual(assessment.state, AssessmentState.UNRESOLVED)


class AssessCandidateConstraintsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.candidate = FusedCandidate(
            "PRODUCT",
            0.3,
            (RouteEvidence("bm25", 1, 8.5),),
        )
        self.record = {
            "parent_asin": "PRODUCT",
            "features": ["Water resistant shell"],
            "price": 80,
        }

    def test_routes_required_claims_in_claim_order(self) -> None:
        result = assess_candidate_constraints(
            self.candidate,
            self.record,
            (
                ObservedClaim("feature", "water resistant", "required"),
                ObservedClaim("budget", "up to $80", "required"),
            ),
        )

        self.assertEqual(result.status, EligibilityStatus.CONFIRMED)
        self.assertEqual(
            tuple(assessment.attribute for assessment in result.assessments),
            ("feature", "budget"),
        )
        self.assertIn("features", result.assessments[0].reason)
        self.assertIn("price", result.assessments[1].reason)

    def test_ignores_preferred_and_indifferent_claims(self) -> None:
        result = assess_candidate_constraints(
            self.candidate,
            self.record,
            (
                ObservedClaim("material", "cotton", "preferred"),
                ObservedClaim("color", None, "indifferent"),
                ObservedClaim("feature", "water resistant", "required"),
            ),
        )

        self.assertEqual(len(result.assessments), 1)
        self.assertEqual(result.assessments[0].attribute, "feature")

    def test_budget_contradiction_makes_candidate_ineligible(self) -> None:
        result = assess_candidate_constraints(
            self.candidate,
            self.record,
            (
                ObservedClaim("feature", "water resistant", "required"),
                ObservedClaim("budget", "under $80", "required"),
            ),
        )

        self.assertEqual(result.status, EligibilityStatus.INELIGIBLE)
        self.assertEqual(
            result.assessments[1].state,
            AssessmentState.CONFIRMED_CONTRADICTION,
        )
        self.assertIn("price", result.assessments[1].reason)

    def test_match_plus_unknown_requirement_is_provisional(self) -> None:
        result = assess_candidate_constraints(
            self.candidate,
            self.record,
            (
                ObservedClaim("feature", "water resistant", "required"),
                ObservedClaim("color", "blue", "required"),
            ),
        )

        self.assertEqual(result.status, EligibilityStatus.PROVISIONAL)
        self.assertEqual(
            tuple(assessment.state for assessment in result.assessments),
            (AssessmentState.CONFIRMED_MATCH, AssessmentState.UNKNOWN),
        )

    def test_no_required_claims_confirms_candidate(self) -> None:
        result = assess_candidate_constraints(
            self.candidate,
            self.record,
            (ObservedClaim("material", "cotton", "preferred"),),
        )

        self.assertEqual(result.status, EligibilityStatus.CONFIRMED)
        self.assertEqual(result.assessments, ())

    def test_preserves_original_candidate_and_raw_record(self) -> None:
        original_record = deepcopy(self.record)
        original_evidence = self.candidate.route_evidence

        result = assess_candidate_constraints(
            self.candidate,
            self.record,
            (ObservedClaim("feature", "water resistant", "required"),),
        )

        self.assertIs(result.candidate, self.candidate)
        self.assertIs(result.candidate.route_evidence, original_evidence)
        self.assertEqual(self.record, original_record)


if __name__ == "__main__":
    unittest.main()
