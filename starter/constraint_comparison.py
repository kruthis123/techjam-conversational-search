from __future__ import annotations

import re
from typing import Sequence

from starter.eligibility import (
    AssessmentState,
    ConstraintAssessment,
    EligibilityResult,
    aggregate_candidate_eligibility,
)
from starter.fusion import FusedCandidate
from starter.intent import ObservedClaim
from starter.price_claims import price_claim


SEARCH_FIELDS = (
    "title",
    "features",
    "details",
    "description",
    "categories",
    "store",
)

BUDGET_CEILING_RE = re.compile(
    r"(?P<relation>\bunder\b|\bup\s+to\b|<=)\s*\$?\s*"
    r"(?P<amount>\d+(?:\.\d+)?)\b",
    re.IGNORECASE,
)


def _text(value: object) -> str:
    if isinstance(value, dict):
        return " ".join(f"{key} {_text(item)}" for key, item in value.items())
    if isinstance(value, list):
        return " ".join(_text(item) for item in value)
    if value is None:
        return ""
    return str(value)


def _tokens(value: object) -> tuple[str, ...]:
    return tuple(re.findall(r"[^\W_]+", _text(value).casefold()))


def assess_observed_text_constraint(
    record: dict[str, object],
    claim: ObservedClaim,
) -> ConstraintAssessment:
    """Assess exact observed text without treating absence as contradiction."""
    claim_tokens = _tokens(claim.value)
    if not claim_tokens:
        return ConstraintAssessment(
            claim.attribute,
            AssessmentState.UNRESOLVED,
            "The claim has no usable value.",
        )

    sequence_length = len(claim_tokens)
    for field in SEARCH_FIELDS:
        field_tokens = _tokens(record.get(field))
        if any(
            field_tokens[index:index + sequence_length] == claim_tokens
            for index in range(len(field_tokens) - sequence_length + 1)
        ):
            return ConstraintAssessment(
                claim.attribute,
                AssessmentState.CONFIRMED_MATCH,
                f"Exact token sequence found in catalog field '{field}'.",
            )

    return ConstraintAssessment(
        claim.attribute,
        AssessmentState.UNKNOWN,
        "No exact token sequence found in supported catalog fields.",
    )


def assess_budget_ceiling(
    record: dict[str, object],
    claim: ObservedClaim,
) -> ConstraintAssessment:
    """Compare a numeric catalog price with one explicit upper budget bound."""
    match = BUDGET_CEILING_RE.search(claim.value or "")
    if match is None:
        return ConstraintAssessment(
            "budget",
            AssessmentState.UNRESOLVED,
            "The budget claim has no supported upper-bound wording.",
        )

    ceiling = float(match.group("amount"))
    catalog_price = price_claim(record)
    if catalog_price is None:
        return ConstraintAssessment(
            "budget",
            AssessmentState.UNKNOWN,
            "Catalog field 'price' has no supported numeric value.",
        )

    relation = match.group("relation").casefold()
    matches = (
        catalog_price.value < ceiling
        if relation == "under"
        else catalog_price.value <= ceiling
    )
    state = (
        AssessmentState.CONFIRMED_MATCH
        if matches
        else AssessmentState.CONFIRMED_CONTRADICTION
    )
    return ConstraintAssessment(
        "budget",
        state,
        f"Catalog field 'price' value {catalog_price.value} compared with "
        f"{relation} ceiling {ceiling}.",
    )


def assess_candidate_constraints(
    candidate: FusedCandidate,
    record: dict[str, object],
    claims: Sequence[ObservedClaim],
) -> EligibilityResult:
    """Assess required claims in order and aggregate candidate eligibility."""
    assessments = []
    for claim in claims:
        if claim.stance != "required":
            continue

        if claim.attribute == "budget":
            assessment = assess_budget_ceiling(record, claim)
        else:
            assessment = assess_observed_text_constraint(record, claim)
        assessments.append(assessment)

    return aggregate_candidate_eligibility(candidate, assessments)
