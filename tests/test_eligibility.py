from __future__ import annotations

from dataclasses import FrozenInstanceError
import unittest

from starter.eligibility import (
    AssessmentState,
    ConstraintAssessment,
    EligibilityResult,
    EligibilityStatus,
    aggregate_candidate_eligibility,
    partition_candidate_eligibility,
)
from starter.fusion import FusedCandidate, RouteEvidence


class AggregateCandidateEligibilityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.candidate = FusedCandidate(
            "PRODUCT",
            0.3,
            (
                RouteEvidence("bm25", 1, 8.5),
                RouteEvidence("facet", 2, 2.0),
            ),
        )

    def test_confirms_candidate_when_all_assessments_match(self) -> None:
        assessments = (
            ConstraintAssessment(
                "category",
                AssessmentState.CONFIRMED_MATCH,
                "Catalog category matches the requested category.",
            ),
            ConstraintAssessment(
                "price",
                AssessmentState.CONFIRMED_MATCH,
                "Catalog price is within the requested limit.",
            ),
        )

        result = aggregate_candidate_eligibility(self.candidate, assessments)

        self.assertEqual(result.status, EligibilityStatus.CONFIRMED)
        self.assertEqual(result.assessments, assessments)

    def test_confirms_candidate_when_there_are_no_assessments(self) -> None:
        result = aggregate_candidate_eligibility(self.candidate, ())

        self.assertEqual(result.status, EligibilityStatus.CONFIRMED)
        self.assertEqual(result.assessments, ())

    def test_each_uncertainty_state_makes_candidate_provisional(self) -> None:
        uncertainty_states = (
            AssessmentState.UNKNOWN,
            AssessmentState.INFERRED,
            AssessmentState.AMBIGUOUS,
            AssessmentState.UNRESOLVED,
        )

        for state in uncertainty_states:
            with self.subTest(state=state):
                assessments = (
                    ConstraintAssessment(
                        "category",
                        AssessmentState.CONFIRMED_MATCH,
                        "Catalog category matches the requested category.",
                    ),
                    ConstraintAssessment("material", state, "Evidence is uncertain."),
                )

                result = aggregate_candidate_eligibility(self.candidate, assessments)

                self.assertEqual(result.status, EligibilityStatus.PROVISIONAL)
                self.assertEqual(result.assessments, assessments)

    def test_contradiction_makes_candidate_ineligible_and_keeps_reason(self) -> None:
        contradiction_reason = "Catalog price exceeds the requested limit."
        assessments = (
            ConstraintAssessment(
                "category",
                AssessmentState.CONFIRMED_MATCH,
                "Catalog category matches the requested category.",
            ),
            ConstraintAssessment(
                "price",
                AssessmentState.CONFIRMED_CONTRADICTION,
                contradiction_reason,
            ),
            ConstraintAssessment(
                "material",
                AssessmentState.UNKNOWN,
                "Catalog material is missing.",
            ),
        )

        result = aggregate_candidate_eligibility(self.candidate, assessments)

        self.assertEqual(result.status, EligibilityStatus.INELIGIBLE)
        self.assertEqual(result.assessments[1].reason, contradiction_reason)
        self.assertEqual(result.assessments, assessments)

    def test_preserves_original_candidate_and_route_evidence(self) -> None:
        original_evidence = self.candidate.route_evidence

        result = aggregate_candidate_eligibility(self.candidate, ())

        self.assertIs(result.candidate, self.candidate)
        self.assertIs(result.candidate.route_evidence, original_evidence)

    def test_assessment_and_result_are_immutable(self) -> None:
        assessment = ConstraintAssessment(
            "category",
            AssessmentState.CONFIRMED_MATCH,
            "Catalog category matches the requested category.",
        )
        result = aggregate_candidate_eligibility(self.candidate, (assessment,))

        with self.assertRaises(FrozenInstanceError):
            assessment.reason = "Changed reason."
        with self.assertRaises(FrozenInstanceError):
            result.status = EligibilityStatus.PROVISIONAL


class PartitionCandidateEligibilityTest(unittest.TestCase):
    def result(
        self,
        parent_asin: str,
        status: EligibilityStatus,
        reason: str = "Evidence is uncertain.",
    ) -> EligibilityResult:
        if status is EligibilityStatus.CONFIRMED:
            state = AssessmentState.CONFIRMED_MATCH
        elif status is EligibilityStatus.PROVISIONAL:
            state = AssessmentState.UNKNOWN
        else:
            state = AssessmentState.CONFIRMED_CONTRADICTION
        return EligibilityResult(
            FusedCandidate(
                parent_asin,
                0.1,
                (RouteEvidence("bm25", 1, 8.5),),
            ),
            status,
            (ConstraintAssessment("budget", state, reason),),
        )

    def test_partitions_interleaved_results_in_original_order(self) -> None:
        confirmed = self.result("A", EligibilityStatus.CONFIRMED)
        ineligible = self.result("B", EligibilityStatus.INELIGIBLE)
        provisional = self.result("C", EligibilityStatus.PROVISIONAL)
        later_confirmed = self.result("D", EligibilityStatus.CONFIRMED)

        retained, excluded = partition_candidate_eligibility(
            (confirmed, ineligible, provisional, later_confirmed)
        )

        self.assertEqual(retained, (confirmed, provisional, later_confirmed))
        self.assertEqual(excluded, (ineligible,))

    def test_preserves_excluded_objects_and_contradiction_reasons(self) -> None:
        first_reason = "Catalog price 90 exceeds ceiling 80."
        second_reason = "Catalog price 120 exceeds ceiling 100."
        first = self.result("A", EligibilityStatus.INELIGIBLE, first_reason)
        retained_result = self.result("B", EligibilityStatus.CONFIRMED)
        second = self.result("C", EligibilityStatus.INELIGIBLE, second_reason)

        _, excluded = partition_candidate_eligibility(
            (first, retained_result, second)
        )

        self.assertIs(excluded[0], first)
        self.assertIs(excluded[1], second)
        self.assertIs(excluded[0].candidate, first.candidate)
        self.assertIs(excluded[0].assessments, first.assessments)
        self.assertEqual(
            tuple(result.assessments[0].reason for result in excluded),
            (first_reason, second_reason),
        )

    def test_empty_input_returns_two_empty_tuples(self) -> None:
        self.assertEqual(partition_candidate_eligibility(()), ((), ()))


if __name__ == "__main__":
    unittest.main()
