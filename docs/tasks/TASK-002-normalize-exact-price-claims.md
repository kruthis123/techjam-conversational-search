# TASK-002: Create simple price claims

- Status: `Verified`
- Owner: `implementer`
- Roadmap milestone: `M1 — Catalog truth, identity, normalization, and provenance`
- Related accepted ADRs: `ADR-002`, `ADR-003`, `ADR-004`

## Goal

For a trusted raw catalog record, return one small source-linked price claim when `price` is numeric; otherwise return `None`.

## Inputs and outputs

Input: one raw record produced by the verified catalog loader.

Output:

- `PriceClaim(parent_asin, value, source_field="price")` for an integer or float price other than a boolean;
- `None` when price is missing, null, or a string.

The function must not modify the raw record.

## Allowed files

- `starter/price_claims.py`
- `tests/test_price_claims.py`

## Non-goals

- No generic claim framework, `Decimal`, currency model, relation model, component scope, confidence, persistence, or index.
- No parsing of em dashes, `from N.NN`, ranges, or other strings.
- No duplicate identity validation already owned by the catalog loader.
- No handling for hypothetical malformed numeric values not present in the fixed catalog.
- No other facets or Agent integration.

## Acceptance criteria

- Given a trusted record with a numeric non-boolean price, when normalization runs, then it returns a `PriceClaim` containing the same `parent_asin`, the unchanged numeric value, and source field `price`.
- Given a record with missing, null, em-dash, or `from N.NN` price, when normalization runs, then it returns `None`.
- Given either path, when the original record is inspected afterwards, then it is unchanged.
- Given the fixed catalog, when all records are processed, then 10,410 price claims are emitted.
- Given the repository test suite, when verification runs, then existing and focused tests pass.

## Test cases

- One numeric price.
- One missing or null price.
- One representative string price.
- Raw record remains unchanged.

## Verification commands

```bash
python3.12 -m unittest tests.test_price_claims -v
python3.12 -m unittest discover -s tests -v
python3.12 -c 'from starter.catalog import load_catalog; from starter.price_claims import price_claim; records = load_catalog("data/catalog.jsonl"); count = sum(price_claim(record) is not None for record in records.values()); assert count == 10410; print(count)'
```

## Risks or assumptions

- This intentionally trusts records loaded by `TASK-001`.
- USD and exact-price semantics are implicit for the first learning experiment.
- The representation may be replaced after a second facet provides evidence for a reusable claim model.

## Implementation evidence

- Numeric, abstention, and non-mutation behavior: `python3.12 -m unittest tests.test_price_claims -v` passed 3/3 tests.
- Repository regression suite: `python3.12 -m unittest discover -s tests -v` passed 15/15 tests.
- Fixed-catalog count: the approved command printed `10410` and exited successfully.

## Review findings and resolution

Independent review found no actionable issue, scope creep, or unnecessary complexity. Independent acceptance verification marked every criterion PASS on `2026-09-18`.

## Approval record

Approved through the user's explicit instruction to implement M1 on `2026-09-18`. This authorizes the simplest bounded implementation but does not authorize Codex to decide the M1 comparison experiment.
