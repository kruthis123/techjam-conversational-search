# TASK-010: Add the single-vector LSA retrieval route

- Status: `Verified`
- Owner: `implementer`
- Roadmap milestone: `M3 — Baseline catalog representations and retrieval routes`
- Related accepted ADRs: `ADR-002`, `ADR-007`

## Goal

Retrieve products by cosine similarity between one deterministic dense LSA vector per product and one vector for the shared textual query.

## Inputs and outputs

Inputs: raw catalog records keyed by `parent_asin`, the shared textual retrieval query, and a requested result depth.

Output: ordered immutable `RetrievalHit` values containing one-based rank and cosine-similarity score.

## Allowed files

- `pyproject.toml`
- `uv.lock`
- `starter/dense_retrieval.py`
- `tests/test_dense_retrieval.py`
- `tests/test_catalog.py`

## Non-goals

- No neural embedding model, model/API download, approximate nearest-neighbour index, multi-view vectors, learned sparse retrieval, token-level multi-vector retrieval, Agent integration, fusion, constraint filtering, or final ranking.
- No broad handling for empty or malformed catalogs beyond the fixed-catalog assumption.

## Acceptance criteria

- Given the runtime manifest, when dependencies are resolved, then `scikit-learn` is the only direct runtime dependency and a lockfile records the resolution for Python 3.12.
- Given raw products, when the route is built, then their field-labelled catalog text is converted to TF-IDF with at most 20,000 features and then to one normalized LSA vector per product using at most 64 dimensions and a fixed random seed.
- Given a query containing known vocabulary, when search runs, then its vector is produced by the fitted transforms and products are ranked by descending cosine similarity.
- Given tied scores, when search runs, then product identity provides deterministic ordering.
- Given an empty or out-of-vocabulary query or nonpositive depth, when search runs, then no hits are returned.
- Given returned hits, when inspected, then ranks are one-based and candidate depth is respected.
- Given the repository test suite under the locked environment, when verification runs, then existing and focused tests pass.

## Test cases

- Relevant product ranks ahead of less similar products.
- Stable identifier tie-break and depth.
- Empty, out-of-vocabulary, and zero-depth query.
- Manifest and locked dependency expectation.

## Verification commands

```bash
unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest tests.test_dense_retrieval -v
unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest discover -s tests -v
```

## Risks or assumptions

- LSA is a simple educational dense-vector baseline, not a claim that it matches a modern neural embedding model. The M3 experiment decides whether its unique coverage justifies keeping it or replacing it later.
- The fixed catalog is large enough for the selected reduction; tests may use a smaller effective dimension while preserving the same bounded rule.

## Implementation evidence

- Focused locked-environment suite: `unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest tests.test_dense_retrieval -v` passed 4/4 tests.
- Repository locked-environment suite: `unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest discover -s tests -v` passed 48/48 tests.
- `uv lock --check` passed. The initial sandboxed command could not access the shared `uv` cache; the identical authorized command resolved the environment and passed. This was an environment-access failure, not a product failure.
- Independent review found no actionable issue and did not run the user-owned full-catalog comparison.
- Independent acceptance verification marked every criterion PASS and confirmed the task stayed within its allowed files.

## Approval record

Approved through the user's explicit instruction to start M3 on `2026-09-22`.
