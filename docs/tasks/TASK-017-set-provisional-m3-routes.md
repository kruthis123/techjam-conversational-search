# TASK-017: Set the provisional M3 routes

- Status: `Verified`
- Owner: `implementer`
- Roadmap milestone: `M3 — Baseline catalog representations and retrieval routes`
- Related accepted ADRs: `ADR-007`, `ADR-009`

## Goal

Expose BM25, facet, and SVD-256 as the provisional three-route retrieval set
without removing any prior experiment implementation or evidence.

## Inputs and outputs

Inputs: catalog records, one retrieval query, and requested candidate depth.

Output: route results and comparison metrics named `lexical`, `facet`, and
`svd_256`.

## Allowed files

- `starter/dense_retrieval.py`
- `experiments/m3_compare_routes.py`
- `tests/test_dense_retrieval.py`
- `tests/test_m3_compare_routes.py`
- `docs/experiments/M3-retrieval-route-comparison.md`
- `docs/PROJECT_STATE.md`

## Non-goals

- No deletion of raw-TFIDF or dense-vectorization experiments.
- No neural embedding, dialogue integration, fusion, filtering, reranking,
  tuning rerun, or holdout run.

## Acceptance criteria

- Given a requested SVD dimension, when the dense retriever is built, then it
  uses that capped dimension while preserving 64 as the default for historical
  experiment compatibility.
- Given the provisional route comparison, when it runs, then lexical, facet,
  and `svd_256` receive the same query and depth and every metric section uses
  those exact route names.
- Given existing dense-vectorization and raw-TFIDF code, when focused regression
  tests run, then those historical experiments remain importable and passing.
- Given CLI help, when requested, then it exits without loading catalog data or
  running retrieval.

## Verification commands

```bash
unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest tests.test_dense_retrieval tests.test_raw_tfidf_retrieval tests.test_m3_compare_dense_variants tests.test_m3_compare_routes -v
unset VIRTUAL_ENV && uv run --python 3.12 python -m experiments.m3_compare_routes --help
```

## Approval record

Approved by the user's explicit instruction on `2026-09-27`.

## Implementation evidence

- `DenseRetriever` keeps 64 dimensions as the historical default and accepts a
  requested capped dimension; the provisional runner constructs `svd_256` with
  `dimensions=256`.
- Every metric section uses `lexical`, `facet`, and `svd_256` consistently.
- Historical raw-TFIDF and dense-vectorization experiments remain importable and
  their focused regressions pass.
- Focused TASK-017 suite passed 21/21 tests.
- Reviewer findings about meaningful dimension evidence and stale holdout
  instructions were corrected with a 257-record dimension test, constructor
  wiring test, and unconditional holdout deferral in the experiment guide.
- No tuning comparison or holdout run was performed during implementation.
