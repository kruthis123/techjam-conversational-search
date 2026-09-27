# TASK-015: Compare dense vectorizations

- Status: `Verified`
- Owner: `implementer`
- Roadmap milestone: `M3 — Baseline catalog representations and retrieval routes`
- Related accepted ADRs: `ADR-007`

## Goal

Compare the current 64-dimensional TF-IDF/LSA baseline with raw TF-IDF cosine
similarity and a 256-dimensional TF-IDF/LSA variant on the same M3 tuning
sessions.

## Inputs and outputs

Inputs: the fixed catalog, public tuning sessions, first-turn retrieval queries,
and one or more candidate depths.

Output: JSON reporting Recall@K, union recall, unique target contribution,
candidate overlap, timing, scenario/difficulty counts, and representative misses
for `svd_64`, `raw_tfidf`, and `svd_256`.

## Allowed files

- `experiments/m3_compare_dense_variants.py`
- `tests/test_m3_compare_dense_variants.py`
- `docs/experiments/M3-dense-vectorization-comparison.md`
- `docs/PROJECT_STATE.md`

## Non-goals

- No change to `starter/dense_retrieval.py` or the active retrieval routes.
- No neural embedding, multi-view representation, field weighting, query change,
  Agent integration, fusion, constraint filtering, or final ranking.
- No holdout run and no automatic selection of a winning variant.

## Acceptance criteria

- Given the catalog, when the comparison index is built, then all three variants
  use the same field-labelled product documents, TF-IDF vocabulary, and product
  order as the current dense baseline.
- Given one first-turn query, when retrieval runs, then `svd_64`, `raw_tfidf`,
  and `svd_256` rank products independently with cosine similarity.
- Given depths 50 and 100, when the tuning comparison runs, then both depths are
  summarized from the same retrieved results and fixed tuning sessions.
- Given completed retrieval outputs, when results are summarized, then target
  labels are used only for evaluation and the output includes recall, union
  recall, unique contribution, overlap, timing, slices, and bounded misses.
- Given the command-line interface, when help is requested, then it explains the
  inputs without loading the catalog or running the experiment.

## Verification commands

```bash
unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest tests.test_m3_compare_dense_variants -v
unset VIRTUAL_ENV && uv run --python 3.12 python -m experiments.m3_compare_dense_variants --help
```

## Approval record

Approved by the user's explicit request to write the dense-vectorization
comparison code on `2026-09-27`.

## Implementation evidence

- Added a tuning-only comparison over one shared TF-IDF matrix for
  `raw_tfidf`, `svd_64`, and `svd_256`.
- The current-compatible `svd_64` branch matches the existing dense baseline's
  vocabulary, product order, and ranking in the focused test.
- Multiple requested depths reuse one maximum-depth retrieval result and are
  summarized separately.
- Target identifiers are used only during result summarization.
- Per-variant search timings independently measure projection, scoring, and
  ranking; shared TF-IDF query transformation is consistently excluded.
- `unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest tests.test_m3_compare_dense_variants -v`
  passed 5/5 tests.
- CLI help and Python compilation passed without loading the catalog or running
  the full experiment.
- Independent acceptance verification marked every criterion PASS. Independent
  review's timing finding was corrected and re-review found no remaining high-
  or medium-priority issue.
- The full tuning comparison and holdout were not run by Codex.
