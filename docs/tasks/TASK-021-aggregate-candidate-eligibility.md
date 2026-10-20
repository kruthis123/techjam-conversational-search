# TASK-021: Aggregate candidate eligibility

- Status: `Verified`
- Owner: `implementer`
- Roadmap milestone: `M4 — Candidate fusion and constraint-aware selection`
- Related accepted ADRs: `ADR-010`, `ADR-011`

## Goal

Classify a fused candidate as confirmed, provisional, or ineligible from its
per-constraint assessment states while preserving all trace evidence.

## Inputs and outputs

Input: one `FusedCandidate` and its ordered constraint assessments.

Output: an immutable eligibility result containing the unchanged fused
candidate, final status, and original assessments.

## Allowed files

- `starter/eligibility.py`
- `tests/test_eligibility.py`
- `docs/tasks/TASK-021-aggregate-candidate-eligibility.md`
- `docs/PROJECT_STATE.md`

## Non-goals

- Reading catalog records or active intent.
- Comparing category, price, material, dimensions, or compatibility.
- Applying the candidate budget.
- Removing ineligible candidates from a sequence.
- Ranking confirmed and provisional candidates.

## Acceptance criteria

- Given only confirmed-match assessments, when eligibility is aggregated, then
  the candidate is confirmed and all assessments are preserved.
- Given no hard-constraint assessments, when eligibility is aggregated, then
  the candidate is confirmed.
- Given any unknown, inferred, ambiguous, or unresolved assessment and no
  contradiction, when eligibility is aggregated, then the candidate is
  provisional.
- Given a confirmed contradiction alongside any other assessments, when
  eligibility is aggregated, then the candidate is ineligible and the
  contradiction reason remains inspectable.
- Given any classification result, when its candidate is inspected, then the
  original fused candidate and route evidence are unchanged.

## Test cases

- Two confirmed matches.
- No assessments.
- Each uncertainty state with a confirmed match.
- A contradiction mixed with a match and unknown state.

## Verification commands

```bash
unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest tests.test_eligibility -v
unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest discover -v
```

## Risks or assumptions

- Typed comparator tasks will supply valid assessment states and traceable
  reasons; broad runtime validation is intentionally deferred.
- This task validates the accepted aggregation policy independently before
  catalog-specific comparisons are added.

## Approval record

Approved under the user's M4 authorization and explicit instruction to proceed
on `2026-10-09`.

## Implementation evidence

- Confirmed eligibility and assessment preservation:
  `test_confirms_candidate_when_all_assessments_match` verifies that two
  confirmed matches produce `confirmed` and retain both ordered assessments.
- Empty-assessment eligibility:
  `test_confirms_candidate_when_there_are_no_assessments` verifies that a
  candidate with no active hard-constraint assessments is `confirmed`.
- Provisional eligibility for every accepted uncertainty state:
  `test_each_uncertainty_state_makes_candidate_provisional` verifies
  `unknown`, `inferred`, `ambiguous`, and `unresolved`, each alongside a
  confirmed match.
- Contradiction precedence and trace evidence:
  `test_contradiction_makes_candidate_ineligible_and_keeps_reason` verifies
  that a contradiction mixed with a match and unknown state produces
  `ineligible` while preserving the contradiction reason and assessment order.
- Candidate and route-evidence preservation:
  `test_preserves_original_candidate_and_route_evidence` verifies that the
  result contains the original `FusedCandidate` object and its original route
  evidence.
- Immutable records: `test_assessment_and_result_are_immutable` verifies that
  both the assessment and aggregate result reject field reassignment.
- Focused verification passed 6/6 tests:
  `unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest tests.test_eligibility -v`.
- Full repository verification passed 83/83 tests:
  `unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest discover -v`.

## Review findings and resolution

- Independent review found no actionable findings.
- Independent verification mapped evidence to every acceptance criterion.
- Focused verification passed 6/6 tests and the complete repository suite
  passed 83/83 tests.
