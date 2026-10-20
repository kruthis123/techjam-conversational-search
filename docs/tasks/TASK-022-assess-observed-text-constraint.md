# TASK-022: Assess an observed-text constraint

- Status: `Verified`
- Owner: `implementer`
- Roadmap milestone: `M4 — Candidate fusion and constraint-aware selection`
- Related accepted ADRs: `ADR-003`, `ADR-011`, `ADR-012`

## Goal

Produce one traceable constraint assessment by looking for a required claim's
complete token sequence in supported raw catalog text fields.

## Inputs and outputs

Input: one preserved raw catalog record and one required `ObservedClaim`.

Output: one `ConstraintAssessment` marked `confirmed_match`, `unknown`, or
`unresolved`, with a reason identifying the matching source field when found.

## Allowed files

- `starter/constraint_comparison.py`
- `tests/test_constraint_comparison.py`
- `docs/tasks/TASK-022-assess-observed-text-constraint.md`
- `docs/PROJECT_STATE.md`

## Non-goals

- Numeric budget comparison.
- Producing confirmed contradictions from missing text.
- Synonyms, aliases, stemming, semantic similarity, or LLM inference.
- Component scope, dimensions, or compatibility.
- Aggregating final eligibility or filtering candidates.

## Acceptance criteria

- Given a case- or punctuation-varied complete token sequence in a supported
  catalog field, when the claim is assessed, then it is a confirmed match and
  the reason names that source field.
- Given the claim tokens only as part of a longer word, when the claim is
  assessed, then it is not confirmed.
- Given no complete observed sequence in any supported field, when the claim is
  assessed, then it is unknown rather than a contradiction.
- Given a claim without a usable value, when it is assessed, then it is
  unresolved.
- Given a raw catalog record, when assessment finishes, then the record remains
  unchanged.

## Test cases

- A multi-word feature with punctuation and case differences.
- `red` against `infrared`.
- A missing phrase.
- A `None` claim value.
- Raw-record equality before and after assessment.

## Verification commands

```bash
unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest tests.test_constraint_comparison -v
unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest discover -v
```

## Risks or assumptions

- The input claim is an active hard requirement; stance filtering remains the
  caller's responsibility.
- The fixed catalog field shapes established in M1 are trusted.

## Approval record

Approved under the user's instruction to proceed autonomously through M4 until
the experiment is ready on `2026-10-09`.

## Implementation evidence

- Exact sequence matching and source-field traceability:
  `test_confirms_complete_sequence_with_case_and_punctuation_changes` verifies
  that `water resistant shell` matches `WATER-resistant shell` in `features`,
  producing `confirmed_match` with `features` named in the reason.
- Whole-token boundary:
  `test_does_not_match_tokens_inside_a_longer_word` verifies that `red` does
  not match `infrared` and remains `unknown`.
- Absence remains unknown:
  `test_returns_unknown_when_sequence_is_absent` verifies that a missing
  phrase produces `unknown`, never `confirmed_contradiction`.
- Missing claim value:
  `test_returns_unresolved_when_claim_has_no_value` verifies that a `None`
  value produces `unresolved`.
- Raw-record preservation: `test_preserves_raw_catalog_record` verifies deep
  equality before and after assessment across scalar, list, null, and nested
  dictionary values.
- Focused verification passed 5/5 tests:
  `unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest tests.test_constraint_comparison -v`.
- Full repository verification passed 88/88 tests:
  `unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest discover -v`.

## Review findings and resolution

- Independent review found no actionable findings.
- Independent verification mapped evidence to every acceptance criterion.
- Focused verification passed 5/5 tests and the complete repository suite
  passed 88/88 tests.
