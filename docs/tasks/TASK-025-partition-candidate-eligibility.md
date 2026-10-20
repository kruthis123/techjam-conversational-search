# TASK-025: Partition retained and excluded candidates

- Status: `Verified`
- Owner: `implementer`
- Roadmap milestone: `M4 — Candidate fusion and constraint-aware selection`
- Related accepted ADRs: `ADR-011`

## Goal

Separate assessed candidates into retained confirmed/provisional results and
excluded ineligible results without losing input order or trace evidence.

## Inputs and outputs

Input: ordered `EligibilityResult` values.

Output: two tuples: retained results followed by excluded results.

## Allowed files

- `starter/eligibility.py`
- `tests/test_eligibility.py`
- `docs/tasks/TASK-025-partition-candidate-eligibility.md`
- `docs/PROJECT_STATE.md`

## Non-goals

- Reordering confirmed versus provisional candidates.
- Relaxing constraints or restoring excluded candidates.
- Ranking or applying the candidate budget.
- Running the M4 experiment.

## Acceptance criteria

- Given confirmed, provisional, and ineligible results, when partitioned, then
  confirmed and provisional results are retained in their original order.
- Given the same results, when partitioned, then only ineligible results are
  excluded in their original order.
- Given an excluded result, when inspected, then its candidate, assessments,
  and contradiction reason are unchanged.
- Given no results, when partitioned, then both outputs are empty tuples.

## Test cases

- Interleaved confirmed, ineligible, and provisional results.
- Two ineligible results with different contradiction reasons.
- Empty input.

## Verification commands

```bash
unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest tests.test_eligibility -v
unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest discover -v
```

## Risks or assumptions

- Eligibility has already been aggregated according to ADR-011.
- The retained tuple deliberately preserves the incoming RRF order; M5 owns
  later ordering.

## Approval record

Approved under the user's instruction to proceed autonomously through M4 until
the experiment is ready on `2026-10-09`.

## Implementation evidence

- Retained and excluded order:
  `test_partitions_interleaved_results_in_original_order` verifies that
  confirmed and provisional results remain retained in their incoming order,
  while only the interleaved ineligible result is excluded.
- Excluded evidence preservation:
  `test_preserves_excluded_objects_and_contradiction_reasons` verifies two
  ineligible results remain in input order and are returned as the original
  objects, preserving candidate identity, assessment identity, and distinct
  contradiction reasons.
- Empty input:
  `test_empty_input_returns_two_empty_tuples` verifies that no results produces
  `((), ())`.
- Focused verification passed 9/9 tests:
  `unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest tests.test_eligibility -v`.
- Full repository verification passed 102/102 tests:
  `unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest discover -v`.

## Review findings and resolution

- Independent review found no actionable findings.
- Independent verification mapped evidence to every acceptance criterion.
- Focused verification passed 9/9 tests and the complete repository suite
  passed 102/102 tests.
