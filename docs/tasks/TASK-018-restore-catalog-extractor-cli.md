# TASK-018: Restore the catalog extractor CLI

- Status: `Verified`
- Owner: `implementer`
- Roadmap milestone: `M3 — Baseline catalog representations and retrieval routes`
- Related accepted ADRs: `ADR-003`

## Goal

Restore the verified positional-ASIN extraction interface while preserving the
user's current saved ASIN inspection list as a no-positional-argument fallback.

## Inputs and outputs

Inputs: optional positional `parent_asin` values, catalog path, output path, and
optional excluded fields.

Output: the selected raw products in positional order, or the saved inspection
selection when no positional identifiers are supplied.

## Allowed files

- `experiments/extract_catalog_products.py`
- `tests/test_extract_catalog_products.py`

## Non-goals

- No changes to catalog data, retrieval behavior, or the saved ASIN values.

## Acceptance criteria

- Positional ASINs override the saved fallback and preserve requested order.
- With no positional ASINs, the existing saved inspection list remains selected.
- Existing exclusion, missing-ASIN, output, and help behavior remains passing.

## Verification commands

```bash
unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest tests.test_extract_catalog_products -v
unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest discover -v
```

## Approval record

Approved as the smallest publication-blocking repair under the user's explicit
instruction to complete and publish M3 on `2026-09-27`.

## Implementation evidence

- Restored positional ASIN input while preserving all 51 saved ASINs unchanged
  as the no-positional fallback.
- Positional order, field exclusion, missing-ASIN behavior, output formatting,
  help text, and fallback selection have automated evidence.
- Focused extractor suite passed 5/5 tests.
- The complete repository suite passed 70/70 tests after the repair.
