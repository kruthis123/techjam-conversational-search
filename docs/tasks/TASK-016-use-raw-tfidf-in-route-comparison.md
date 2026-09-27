# TASK-016: Use raw TF-IDF in the final M3 route comparison

- Status: `Verified`
- Owner: `implementer`
- Roadmap milestone: `M3 — Baseline catalog representations and retrieval routes`
- Related accepted ADRs: `ADR-007`, `ADR-008`

## Goal

Let the user compare lexical, facet, and raw TF-IDF retrieval on the existing
fixed M3 tuning sessions.

## Inputs and outputs

Inputs: the catalog, first-turn tuning queries, and requested candidate depth.

Output: the existing route-comparison JSON with route names `lexical`, `facet`,
and `raw_tfidf`.

## Allowed files

- `starter/raw_tfidf_retrieval.py`
- `experiments/m3_compare_routes.py`
- `tests/test_raw_tfidf_retrieval.py`
- `tests/test_m3_compare_routes.py`
- `docs/experiments/M3-retrieval-route-comparison.md`
- `docs/PROJECT_STATE.md`

## Non-goals

- No change to the preserved LSA implementation or dense-vectorization runner.
- No neural embeddings, dialogue integration, query change, fusion, filtering,
  final route choice, full comparison run, or holdout access.

## Acceptance criteria

- Given catalog records, when raw TF-IDF is built, then it uses the same six
  field-labelled document fields and 20,000-feature TF-IDF configuration as the
  accepted diagnostic experiment.
- Given a non-empty in-vocabulary query, when raw TF-IDF searches, then it ranks
  normalized TF-IDF cosine scores with deterministic product-ID tie-breaking.
- Given the final route comparison, when it runs, then lexical, facet, and
  `raw_tfidf` receive the same query and requested depth and are reported under
  those exact names.
- Given CLI help, when requested, then it exits without loading the catalog or
  running retrieval.

## Verification commands

```bash
unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest tests.test_raw_tfidf_retrieval tests.test_m3_compare_routes -v
unset VIRTUAL_ENV && uv run --python 3.12 python -m experiments.m3_compare_routes --help
```

## Approval record

Approved by the user's explicit request on `2026-09-27`.

## Implementation evidence

- Added a clearly named raw TF-IDF retriever using the diagnostic experiment's
  field-labelled documents, 20,000-feature cap, normalization, cosine-equivalent
  scoring, and deterministic tie-breaking.
- The final runner now reports exactly `lexical`, `facet`, and `raw_tfidf` in
  recall, unique contribution, overlap, timing, slice, and miss sections.
- Preserved the earlier LSA route and dense-vectorization comparison unchanged.
- `unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest tests.test_raw_tfidf_retrieval tests.test_m3_compare_routes -v`
  passed 9/9 tests.
- CLI help and compilation passed without loading the catalog or running the
  full comparison.
- Independent acceptance verification marked every criterion PASS; independent
  review reported no actionable findings.
- The full tuning comparison and holdout were not run by Codex.
