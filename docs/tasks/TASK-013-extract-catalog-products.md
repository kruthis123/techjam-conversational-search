# TASK-013: Extract selected catalog products for inspection

- Status: `Verified`
- Owner: `implementer`
- Roadmap milestone: `M3 — Baseline catalog representations and retrieval routes`
- Related accepted ADRs: `ADR-003`

## Goal

Provide a small command-line utility that writes selected raw catalog products as readable, pretty-printed JSON for manual retrieval-failure inspection.

## Inputs and outputs

Inputs: one or more `parent_asin` values, the JSONL catalog path, an output path, and an optional blacklist of top-level catalog fields.

Output: one JSON array containing the selected products in requested order, with blacklisted top-level fields omitted. When no blacklist is supplied, every raw field is preserved.

If any requested ASIN is absent, the command exits with an error and does not write a partial output file.

## Allowed files

- `experiments/extract_catalog_products.py`
- `tests/test_extract_catalog_products.py`
- `docs/experiments/M3-retrieval-route-comparison.md`

## Non-goals

- No catalog mutation, nested-field filtering, derived claims, search, retrieval, ranking, output schema abstraction, or full-catalog export.
- No change to the existing raw catalog loader or official data.

## Acceptance criteria

- Given requested ASINs, when extraction runs, then matching raw records are returned in requested order.
- Given no excluded fields, when the output is written, then all raw top-level fields are present and formatted as indented JSON.
- Given excluded top-level fields, when the output is written, then only those fields are omitted from every selected product.
- Given a missing requested ASIN, when extraction runs, then it reports the missing identifier and does not write a partial output file.
- Given the CLI, when help is requested, then it documents positional ASINs, `--catalog`, required `--output`, and optional `--exclude` arguments without loading the catalog.
- Given the focused and repository suites, when verification runs, then they pass without running the M3 comparison or accessing holdout results.

## Test cases

- Requested-order extraction with all fields.
- Top-level blacklist filtering.
- Missing ASIN leaves no output file.
- CLI help.

## Verification commands

```bash
unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest tests.test_extract_catalog_products -v
unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest discover -s tests -v
```

## Risks or assumptions

- The repository catalog is JSON Lines despite the informal `catalog.json` wording; the default is therefore `data/catalog.jsonl`.
- The utility reuses the verified M1 loader and is intended for small manual selections, so loading the fixed catalog into memory is acceptable for this learning workflow.

## Implementation evidence

- Requested-order extraction is covered by a complete-record comparison containing nested dictionaries, lists, nulls, numbers, and strings.
- No-blacklist output preserves every raw top-level field and writes an indented JSON array.
- Blacklist coverage confirms only requested top-level fields are removed.
- Missing-ASIN coverage confirms a clear error and no partial output file.
- CLI help covers positional ASINs, the default catalog path, required output path, and optional top-level exclusions.
- Focused locked-environment suite: `unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest tests.test_extract_catalog_products -v` passed 4/4 tests.
- Repository locked-environment suite: `unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest discover -s tests -v` passed 57/57 tests.
- The M3 comparison was not run and holdout results were not accessed.

## Review findings and resolution

Initial review found that full raw-value preservation was not asserted and CLI argument descriptions were too sparse. The implementer added complete heterogeneous-record equality checks and concise argument help. Final review found no actionable issue, and final acceptance verification marked every criterion PASS.

## Approval record

Approved by the user's explicit request for the extraction script on `2026-09-27`, within the active M3 experiment workflow.
