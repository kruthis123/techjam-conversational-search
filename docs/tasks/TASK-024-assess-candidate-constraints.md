# TASK-024: Assess a candidate's active hard constraints

- Status: `Verified`
- Owner: `implementer`
- Roadmap milestone: `M4 — Candidate fusion and constraint-aware selection`
- Related accepted ADRs: `ADR-011`, `ADR-012`, `ADR-013`

## Goal

Route each active required claim to the accepted comparator and return one
aggregated eligibility result for a fused candidate.

## Inputs and outputs

Input: one `FusedCandidate`, its preserved raw catalog record, and ordered
active intent claims.

Output: one `EligibilityResult` containing assessments for required claims only.

## Allowed files

- `starter/constraint_comparison.py`
- `tests/test_constraint_comparison.py`
- `docs/tasks/TASK-024-assess-candidate-constraints.md`
- `docs/PROJECT_STATE.md`

## Non-goals

- Adding new comparator semantics.
- Treating preferred or indifferent claims as hard constraints.
- Removing ineligible candidates from the sequence.
- Ranking confirmed and provisional candidates.
- Running the M4 experiment.

## Acceptance criteria

- Given required budget and non-budget claims, when a candidate is assessed,
  then each claim is routed to its accepted comparator in claim order.
- Given preferred or indifferent claims, when a candidate is assessed, then
  those claims do not create hard-constraint assessments.
- Given a confirmed contradiction among the required claims, when results are
  aggregated, then the candidate is ineligible and the reason is preserved.
- Given a confirmed match plus an unknown required claim, when aggregated, then
  the candidate is provisional.
- Given no required claims, when assessed, then the candidate is confirmed.
- Given any result, when inspected, then the original fused candidate and raw
  catalog record remain unchanged.

## Test cases

- Exact feature match plus inclusive budget match.
- Preferred and indifferent claims mixed with a requirement.
- Over-budget contradiction alongside a text match.
- Text match plus unknown text requirement.
- No required claims.

## Verification commands

```bash
unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest tests.test_constraint_comparison -v
unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest discover -v
```

## Risks or assumptions

- M2 active state already ensures one current claim per attribute.
- Budget dispatch uses `attribute == "budget"`; every other required claim uses
  the conservative observed-text comparator.

## Approval record

Approved under the user's instruction to proceed autonomously through M4 until
the experiment is ready on `2026-10-09`.

## Implementation evidence

- Required-claim dispatch and order:
  `test_routes_required_claims_in_claim_order` verifies that an observed-text
  feature and inclusive budget claim are assessed by their accepted
  comparators in original claim order, producing a confirmed candidate.
- Non-required claims:
  `test_ignores_preferred_and_indifferent_claims` verifies that preferred and
  indifferent claims produce no hard-constraint assessments while the required
  claim remains.
- Contradiction aggregation and trace preservation:
  `test_budget_contradiction_makes_candidate_ineligible` verifies that an
  over-budget contradiction alongside a text match produces `ineligible` and
  retains the price reason.
- Mixed match and uncertainty:
  `test_match_plus_unknown_requirement_is_provisional` verifies that one text
  match plus one unknown required text claim produces `provisional` in claim
  order.
- Empty hard-constraint set:
  `test_no_required_claims_confirms_candidate` verifies that no required
  claims produces `confirmed` with no assessments.
- Input preservation:
  `test_preserves_original_candidate_and_raw_record` verifies object identity
  for the fused candidate and route evidence, plus deep equality of the raw
  catalog record before and after assessment.
- Focused verification passed 16/16 tests:
  `unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest tests.test_constraint_comparison -v`.
- Full repository verification passed 99/99 tests:
  `unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest discover -v`.

## Review findings and resolution

- Independent review found no actionable findings.
- Independent verification mapped evidence to every acceptance criterion.
- Focused verification passed 16/16 tests and the complete repository suite
  passed 99/99 tests.
