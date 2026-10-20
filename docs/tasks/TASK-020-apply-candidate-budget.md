# TASK-020: Apply the post-fusion candidate budget

- Status: `Verified`
- Owner: `implementer`
- Roadmap milestone: `M4 — Candidate fusion and constraint-aware selection`
- Related accepted ADRs: `ADR-010`

## Goal

Return a configurable number of candidates from the complete RRF-ordered union
without changing candidate order or route evidence.

## Inputs and outputs

Input: ordered fused candidates and a candidate limit.

Output: the first `limit` fused candidates. A non-positive limit returns an
empty tuple; a limit larger than the union returns the complete union.

## Allowed files

- `starter/fusion.py`
- `tests/test_fusion.py`
- `docs/tasks/TASK-020-apply-candidate-budget.md`
- `docs/PROJECT_STATE.md`

## Non-goals

- Selecting the final candidate limit.
- Running the M4 comparison experiment.
- Changing RRF scores or ordering.
- Reserving candidates per route.
- Checking constraints or assigning eligibility.

## Acceptance criteria

- Given more fused candidates than the requested limit, when the budget is
  applied, then only the first `limit` candidates are returned in the same
  order with unchanged evidence.
- Given a limit at least as large as the fused union, when the budget is
  applied, then the complete union is returned.
- Given a non-positive limit, when the budget is applied, then an empty tuple
  is returned.

## Test cases

- Limit two candidates from a three-candidate fused union.
- Use a limit larger than the union.
- Use zero as the limit.

## Verification commands

```bash
unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest tests.test_fusion -v
unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest discover -v
```

## Risks or assumptions

- The input is already in deterministic RRF order.
- Candidate-limit selection remains a user-owned M4 experiment rather than an
  implementation default.

## Approval record

Approved under the user's M4 authorization and explicit instruction to
continue the remaining implementation on `2026-10-09`.

## Implementation evidence

- Limited output with unchanged order and evidence:
  `test_limits_candidates_without_changing_order_or_evidence` verifies that a
  limit of two returns the first two objects from a three-candidate fused
  union, including their original route evidence.
- Limit at least as large as the union:
  `test_returns_complete_union_when_limit_is_larger` verifies that a larger
  limit returns the complete ordered tuple.
- Non-positive limit: `test_returns_empty_tuple_when_limit_is_zero` verifies
  the task's zero-limit case returns an empty tuple; the implementation uses
  the same explicit branch for all limits less than or equal to zero.
- Focused verification passed 7/7 tests:
  `unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest tests.test_fusion -v`.
- Full repository verification passed 77/77 tests:
  `unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest discover -v`.

## Review findings and resolution

- Independent review found no actionable findings.
- Independent verification mapped evidence to all three acceptance criteria.
- Focused verification passed 7/7 tests and the complete repository suite
  passed 77/77 tests.
