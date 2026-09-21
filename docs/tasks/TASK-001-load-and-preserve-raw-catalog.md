# TASK-001: Load and preserve raw catalog records

- Status: `Verified`
- Approved by user: `2026-09-17`
- Owner: `implementer`
- Roadmap milestone: `M1 — Catalog truth, identity, normalization, and provenance`
- Related accepted ADRs: `ADR-002`, `ADR-003`

## Goal

Under the pinned Python 3.12 runtime, load a catalog JSONL file into unique `parent_asin`-addressable raw records without coercing, normalizing, enriching, or silently merging catalog evidence.

## Inputs and outputs

Input:

- a filesystem path to a UTF-8 JSONL catalog;
- each non-empty line must decode to a JSON object with a non-empty string `parent_asin`.

Output:

- a mapping keyed by `parent_asin`;
- each value is the complete decoded raw object from that product's line;
- iteration or retrieval must not rewrite the input file or add derived fields to the stored raw record.

Failure behavior:

- a missing file remains a clear file-not-found failure;
- malformed JSON, a non-object row, missing or blank `parent_asin`, or a duplicate `parent_asin` fails deterministically;
- content failures identify the input path and one-based line number;
- partial output is not returned after a validation failure.

## Allowed files

- `pyproject.toml`
- `starter/catalog.py`
- `tests/test_catalog.py`

## Non-goals

- Do not modify `data/catalog.jsonl`, `data/public_set.jsonl`, evaluator code, public labels, or official contract files.
- Do not normalize facets, coerce prices, infer attributes, create derived claims, or define provenance records.
- Do not build lexical, facet, dense, or other indexes.
- Do not connect the loader to `starter.Agent` yet.
- Do not add external runtime dependencies, a lock file, caching, persistence, logging infrastructure, or performance optimization.
- Do not validate domain-specific fields beyond JSON-object shape and `parent_asin` identity.

## Acceptance criteria

- Given a valid fixture containing nested dictionaries, lists, nulls, strings, and numbers, when the catalog is loaded, then the result is keyed by `parent_asin` and every stored raw record equals the corresponding decoded JSON object without added, removed, or coerced fields.
- Given two valid records with different `parent_asin` values, when the catalog is loaded, then both identities are present exactly once and retain file order when the mapping is iterated.
- Given malformed JSON, a non-object row, a missing or blank `parent_asin`, or a repeated `parent_asin`, when loading reaches that row, then loading fails with a diagnostic containing the path and one-based line number and returns no partial catalog.
- Given a nonexistent catalog path, when loading is attempted, then a clear file-not-found failure identifies that path.
- Given the official `data/catalog.jsonl`, when the loader is run under Python 3.12, then it produces 50,000 unique records and leaves the catalog SHA-256 unchanged.
- Given the project manifest, when it is inspected, then it requires Python `>=3.12,<3.13` and declares no external runtime dependencies.
- Given the repository's pre-existing evaluator tests, when the task's full verification command runs, then those tests still pass unchanged.

## Test cases

- Normal fixture with two records and representative nested/raw value types.
- Empty file, producing an empty mapping.
- Malformed JSON at a known line.
- Valid JSON scalar or list instead of an object.
- Missing, null, non-string, empty, and whitespace-only `parent_asin`.
- Duplicate `parent_asin` on a later line.
- Missing file.
- Official 50,000-row catalog smoke check.
- Manifest/runtime inspection.

## Verification commands

```bash
python3.12 -m unittest tests.test_catalog -v
python3.12 -m unittest discover -s tests -v
python3.12 -c 'from starter.catalog import load_catalog; records = load_catalog("data/catalog.jsonl"); assert len(records) == 50000; assert len(records) == len(set(records)); print(len(records))'
python3.12 -c 'import pathlib, tomllib; data = tomllib.loads(pathlib.Path("pyproject.toml").read_text()); assert data["project"]["requires-python"] == ">=3.12,<3.13"; assert data["project"].get("dependencies", []) == []'
shasum -a 256 data/catalog.jsonl
```

Expected catalog SHA-256 before and after implementation:

```text
da979b05a68af864cb0dcf9ee6a81c010c7e66a57978ad286c7a2e005fc69a67
```

## Risks or assumptions

- Catalog-owned raw mappings are treated as read-only by consumers; this task preserves raw shapes but does not introduce a second canonical typed model.
- Returning a normal Python mapping does not physically prevent a future consumer from mutating nested objects. The module ownership invariant, focused tests, and review must reject such mutation; stronger encapsulation is a revisit only if evidence shows this is insufficient.
- The local catalog reproduces the recorded evaluator baseline, but this task does not independently compare its digest with an absent published `SHA256SUMS` file.
- Source module placement in `starter/catalog.py` is a local, reversible task detail and does not decide the layout of later capabilities.

## Implementation evidence

- Raw preservation and insertion order: `CatalogTest.test_loads_complete_raw_records_in_file_order` passed.
- Content failures with path and physical line: malformed JSON, non-object, invalid identity, and duplicate-identity focused tests passed.
- Missing path behavior: `CatalogTest.test_missing_file_raises_file_not_found_with_path` passed.
- Official catalog: loaded 50,000 unique records and preserved SHA-256 `da979b05a68af864cb0dcf9ee6a81c010c7e66a57978ad286c7a2e005fc69a67`.
- Runtime manifest: Python `>=3.12,<3.13` and empty dependency list verified.
- Focused command: `python3.12 -m unittest tests.test_catalog -v` — 9 tests passed.
- Full regression command: `python3.12 -m unittest discover -s tests -v` — 12 tests passed.
- Independent reviewer: `No actionable findings`; no acceptance criterion lacked static evidence.
- Independent acceptance verifier: all seven acceptance criteria `PASS`.
- Independent focused command: 9/9 tests passed under Python 3.12.14.
- Independent full regression command: 12/12 tests passed under Python 3.12.14.
- Independent catalog smoke, manifest inspection, and SHA-256 commands passed.
- Nondeterminism: none observed; checks use fixed local inputs without network, randomness, or time-dependent assertions.

## Review findings and resolution

Independent reviewer result: `No actionable findings`.

No correction or waiver was required.
