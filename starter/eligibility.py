from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from starter.fusion import FusedCandidate


class AssessmentState(str, Enum):
    CONFIRMED_MATCH = "confirmed_match"
    CONFIRMED_CONTRADICTION = "confirmed_contradiction"
    UNKNOWN = "unknown"
    INFERRED = "inferred"
    AMBIGUOUS = "ambiguous"
    UNRESOLVED = "unresolved"


class EligibilityStatus(str, Enum):
    CONFIRMED = "confirmed"
    PROVISIONAL = "provisional"
    INELIGIBLE = "ineligible"


@dataclass(frozen=True)
class ConstraintAssessment:
    attribute: str
    state: AssessmentState
    reason: str


@dataclass(frozen=True)
class EligibilityResult:
    candidate: FusedCandidate
    status: EligibilityStatus
    assessments: tuple[ConstraintAssessment, ...]


def aggregate_candidate_eligibility(
    candidate: FusedCandidate,
    assessments: Sequence[ConstraintAssessment],
) -> EligibilityResult:
    """Classify a candidate while preserving its ordered assessments."""
    preserved_assessments = tuple(assessments)

    if any(
        assessment.state is AssessmentState.CONFIRMED_CONTRADICTION
        for assessment in preserved_assessments
    ):
        status = EligibilityStatus.INELIGIBLE
    elif all(
        assessment.state is AssessmentState.CONFIRMED_MATCH
        for assessment in preserved_assessments
    ):
        status = EligibilityStatus.CONFIRMED
    else:
        status = EligibilityStatus.PROVISIONAL

    return EligibilityResult(candidate, status, preserved_assessments)


def partition_candidate_eligibility(
    results: Sequence[EligibilityResult],
) -> tuple[tuple[EligibilityResult, ...], tuple[EligibilityResult, ...]]:
    """Return retained then excluded results without changing their order."""
    retained = []
    excluded = []

    for result in results:
        if result.status is EligibilityStatus.INELIGIBLE:
            excluded.append(result)
        else:
            retained.append(result)

    return tuple(retained), tuple(excluded)
