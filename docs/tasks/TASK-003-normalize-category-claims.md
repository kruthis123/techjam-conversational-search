# TASK-003: Create simple category claims

- Status: `Verified`
- Owner: `implementer`
- Roadmap milestone: `M1 — Catalog truth, identity, normalization, and provenance`
- Related accepted ADRs: `ADR-002`, `ADR-003`, `ADR-005`

## Goal

For a trusted raw catalog record, return ordered, normalized, source-linked category claims without modifying the record.

## Inputs and outputs

Input: one raw record produced by the verified catalog loader.

Output: a tuple of `CategoryClaim(parent_asin, value, source_field="categories")` values. Category text is normalized with `strip().casefold()` and repeated normalized values are removed while preserving first occurrence.

## Allowed files

- `starter/category_claims.py`
- `tests/test_category_claims.py`

## Non-goals

- No general claim framework, alias dictionary, taxonomy, hierarchy model, material extraction, persistence, index, or Agent integration.
- No validation for category shapes absent from the fixed catalog.
- No change to price claims or the catalog loader.

## Acceptance criteria

- Given a trusted record with category strings, when normalization runs, then it returns source-ordered lowercase category claims linked to `categories`.
- Given repeated categories that normalize to the same value, when normalization runs, then only the first claim remains.
- Given normalization, when the raw record is inspected afterwards, then it is unchanged.
- Given the fixed catalog, when all records are processed, then 238,277 category claims are emitted.
- Given the repository test suite, when verification runs, then existing and focused tests pass.

## Test cases

- Normal source-ordered categories.
- Whitespace, case normalization, and duplicate removal in one compact example.
- Raw record remains unchanged.

## Verification commands

```bash
python3.12 -m unittest tests.test_category_claims -v
python3.12 -m unittest discover -s tests -v
python3.12 -c 'from starter.catalog import load_catalog; from starter.category_claims import category_claims; records = load_catalog("data/catalog.jsonl"); count = sum(len(category_claims(record)) for record in records.values()); assert count == 238277; print(count)'
```

## Risks or assumptions

- This intentionally trusts records loaded by `TASK-001`.
- Category aliases and hierarchy remain separate future learning questions.
- Whether price and category should share a general claim type is deliberately left to the user experiment.

## Implementation evidence

- Normalization, ordering, deduplication, provenance, and non-mutation behavior: `python3.12 -m unittest tests.test_category_claims -v` passed 3/3 tests.
- Repository regression suite: `python3.12 -m unittest discover -s tests -v` passed 18/18 tests.
- Fixed-catalog count: the approved command printed `238277` and exited successfully.

## Review findings and resolution

Independent review found no actionable issue, scope creep, or unnecessary complexity. Independent acceptance verification marked every criterion PASS on `2026-09-18`.

## Approval record

Approved through the user's explicit instruction to implement M1 on `2026-09-18`, after TASK-002 verification. This authorizes the simple category baseline but leaves the representation comparison to the user experiment.
