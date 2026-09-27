# TASK-008: Add the lexical retrieval route

- Status: `Verified`
- Owner: `implementer`
- Roadmap milestone: `M3 — Baseline catalog representations and retrieval routes`
- Related accepted ADRs: `ADR-007`

## Goal

Retrieve a deterministic top-K list from raw catalog text with a small local BM25-style lexical route.

## Inputs and outputs

Inputs: raw catalog records keyed by `parent_asin`, the shared textual retrieval query, and a requested result depth.

Output: ordered immutable `RetrievalHit` values containing route-local rank and score.

## Allowed files

- `starter/lexical_retrieval.py`
- `tests/test_lexical_retrieval.py`

## Non-goals

- No Agent integration, persistent on-disk index, configurable field weights, phrase or Boolean query language, synonym expansion, facet/dense retrieval, fusion, constraint filtering, or final ranking.
- No broad malformed-catalog hardening beyond the raw-catalog contract already established in M1.

## Acceptance criteria

- Given raw products, when the route is built, then title, categories, features, details, store, and description are searchable through an in-memory SQLite FTS5 index.
- Given a multi-token query, when search runs, then products matching any normalized query token can be returned and better BM25 matches rank first.
- Given tied retrieval scores, when search runs, then product identity provides deterministic ordering.
- Given an empty query or nonpositive depth, when search runs, then no hits are returned.
- Given returned hits, when inspected, then ranks are one-based and scores are ordered from best to worst.
- Given the repository test suite, when verification runs, then existing and focused tests pass.

## Test cases

- Stronger lexical match ranks ahead of a partial match.
- Nested details and list-valued fields are searchable.
- Stable identifier tie-break.
- Empty query and zero depth.

## Verification commands

```bash
python3.12 -m unittest tests.test_lexical_retrieval -v
python3.12 -m unittest discover -s tests -v
```

## Risks or assumptions

- Query tokens are normalized before being passed to FTS5 so simulator punctuation is not interpreted as search syntax.
- The route uses SQLite's default FTS5 field weights until the M3 experiment supplies evidence for weighting fields differently.

## Implementation evidence

- Focused suite: `python3.12 -m unittest tests.test_lexical_retrieval -v` passed 4/4 tests.
- Repository suite: `python3.12 -m unittest discover -s tests -v` passed 40/40 tests.
- Independent review found no actionable issue and confirmed punctuation-safe MATCH construction, deterministic tie-breaking, and intentionally minimal scope.
- Independent acceptance verification marked every criterion PASS and confirmed only the two allowed implementation files changed for this task.

## Approval record

Approved through the user's explicit instruction to start M3 on `2026-09-22`.
