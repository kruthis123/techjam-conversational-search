# TASK-009: Add the category-facet retrieval route

- Status: `Verified`
- Owner: `implementer`
- Roadmap milestone: `M3 — Baseline catalog representations and retrieval routes`
- Related accepted ADRs: `ADR-005`, `ADR-007`

## Goal

Retrieve products whose normalized category facets overlap the shared textual query.

## Inputs and outputs

Inputs: raw catalog records keyed by `parent_asin`, the shared textual retrieval query, and a requested result depth.

Output: ordered immutable `RetrievalHit` values scored by the number of distinct matching category tokens.

## Allowed files

- `starter/facet_retrieval.py`
- `tests/test_facet_retrieval.py`

## Non-goals

- No inferred facets, price-range matching, attribute aliases, phrase semantics, stance weights, configurable weights, Agent integration, lexical/dense retrieval, fusion, constraint filtering, or final ranking.
- No changes to M1 category-claim normalization.

## Acceptance criteria

- Given raw products, when the route is built, then it reuses M1 normalized category claims to create a category-token inverted index.
- Given a query, when search runs, then each product is scored once by its number of distinct matching category tokens.
- Given products matching more distinct category tokens, when search runs, then they rank ahead of products matching fewer tokens.
- Given tied scores, when search runs, then product identity provides deterministic ordering.
- Given no matching tokens, an empty query, or nonpositive depth, when search runs, then no hits are returned.
- Given returned hits, when inspected, then ranks are one-based and candidate depth is respected.
- Given the repository test suite, when verification runs, then existing and focused tests pass.

## Test cases

- Multi-token category overlap and rank order.
- Repeated query/category tokens count once.
- Stable identifier tie-break.
- No match, empty query, and zero depth.

## Verification commands

```bash
python3.12 -m unittest tests.test_facet_retrieval -v
python3.12 -m unittest discover -s tests -v
```

## Risks or assumptions

- Token overlap is a deliberately weak but inspectable facet baseline. It cannot understand category synonyms or other attributes; those limitations are evidence for later representation work rather than reasons to expand M3 now.

## Implementation evidence

- Focused suite: `python3.12 -m unittest tests.test_facet_retrieval -v` passed 4/4 tests.
- Repository suite: `python3.12 -m unittest discover -s tests -v` passed 44/44 tests.
- Independent review found no actionable issue and confirmed distinct-token scoring, deterministic ordering, and reuse of M1 normalization.
- Independent acceptance verification marked every criterion PASS and confirmed only the two allowed implementation files changed for this task.

## Approval record

Approved through the user's explicit instruction to start M3 on `2026-09-22`.
