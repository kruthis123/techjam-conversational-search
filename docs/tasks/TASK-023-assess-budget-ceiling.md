# TASK-023: Assess an explicit budget ceiling

- Status: `Verified`
- Owner: `implementer`
- Roadmap milestone: `M4 — Candidate fusion and constraint-aware selection`
- Related accepted ADRs: `ADR-004`, `ADR-011`, `ADR-013`

## Goal

Compare an explicit upper-budget requirement with a numeric catalog price and
produce one traceable match, contradiction, unknown, or unresolved assessment.

## Inputs and outputs

Input: one preserved raw catalog record and one budget `ObservedClaim`.

Output: one `ConstraintAssessment` for the `budget` attribute.

## Allowed files

- `starter/constraint_comparison.py`
- `tests/test_constraint_comparison.py`
- `docs/tasks/TASK-023-assess-budget-ceiling.md`
- `docs/PROJECT_STATE.md`

## Non-goals

- Approximate, minimum, equality, range, or currency-conversion semantics.
- Parsing catalog string prices.
- Comparing non-budget attributes.
- Aggregating eligibility or filtering candidates.

## Acceptance criteria

- Given `under X` and a numeric price below X, when assessed, then the result is
  a confirmed match.
- Given `under X` and a numeric price equal to or above X, when assessed, then
  the result is a confirmed contradiction.
- Given `up to X` or `<= X` and a numeric price equal to X, when assessed, then
  the result is a confirmed match.
- Given a supported upper bound but no numeric catalog price, when assessed,
  then the result is unknown rather than contradiction.
- Given unsupported budget wording such as `around X`, when assessed, then the
  result is unresolved.
- Given any supported numeric comparison, when its reason is inspected, then it
  names the raw `price` field and compared values.

## Test cases

- Price below a strict ceiling.
- Price equal to and above a strict ceiling.
- Price equal to both inclusive ceiling forms.
- Missing and string catalog prices.
- `budget around $80`.

## Verification commands

```bash
unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest tests.test_constraint_comparison -v
unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest discover -v
```

## Risks or assumptions

- The caller routes only budget claims to this comparator.
- Numeric prices use the fixed catalog's implicit currency; conversion is
  intentionally unsupported.

## Approval record

Approved under the user's instruction to proceed autonomously through M4 until
the experiment is ready on `2026-10-09`.

## Implementation evidence

- Strict ceiling match and traceability:
  `test_price_below_strict_ceiling_is_confirmed` verifies that `79.99` under
  `80` produces `confirmed_match`, with `price`, `79.99`, and `80.0` retained
  in the reason.
- Strict boundary and violation:
  `test_price_equal_to_or_above_strict_ceiling_is_contradicted` verifies that
  prices equal to and above an `under 80` ceiling produce
  `confirmed_contradiction`.
- Inclusive forms:
  `test_price_equal_to_inclusive_ceiling_is_confirmed` verifies equality for
  both `up to $80` and `<= 80` produces `confirmed_match`.
- Unsupported catalog prices:
  `test_missing_or_unsupported_catalog_price_is_unknown` verifies missing,
  null, string, and boolean prices produce `unknown`.
- Unsupported wording:
  `test_unsupported_budget_wording_is_unresolved` verifies
  `budget around $80` produces `unresolved`.
- Focused verification passed 10/10 tests:
  `unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest tests.test_constraint_comparison -v`.
- Full repository verification passed 93/93 tests:
  `unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest discover -v`.

## Review findings and resolution

- Independent review found no actionable findings.
- Independent verification mapped evidence to every acceptance criterion.
- Focused verification passed 10/10 tests and the complete repository suite
  passed 93/93 tests.
