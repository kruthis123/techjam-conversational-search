# TASK-007: Build the shared retrieval query and route hit

- Status: `Verified`
- Owner: `implementer`
- Roadmap milestone: `M3 — Baseline catalog representations and retrieval routes`
- Related accepted ADRs: `ADR-007`

## Goal

Translate current active intent into one deterministic textual retrieval query and define the common route-local hit returned by every M3 retriever.

## Inputs and outputs

Input: ordered active `ObservedClaim` values from M2.

Outputs: one query string and an immutable hit containing product identity, route-local rank, and route-local score.

## Allowed files

- `starter/retrieval.py`
- `tests/test_retrieval.py`

## Non-goals

- No catalog access, indexing, retrieval route, Agent integration, fusion, constraint filtering, ranking, inference, or query expansion.
- No general query language or configurable pipeline.

## Acceptance criteria

- Given ordered active claims, when query construction runs, then nonempty non-indifferent values are joined in stored order.
- Given repeated claim values, when query construction runs, then repeated text is included once.
- Given indifferent or blank claims, when query construction runs, then they contribute no query text.
- Given a route result, when represented as a hit, then product identity, one-based route-local rank, and score are available from an immutable value.
- Given the repository test suite, when verification runs, then existing and focused tests pass.

## Test cases

- Ordered required and preferred values.
- Indifferent, blank, and repeated values.
- Immutable route-local hit.

## Verification commands

```bash
python3.12 -m unittest tests.test_retrieval -v
python3.12 -m unittest discover -s tests -v
```

## Risks or assumptions

- A single joined query intentionally preserves little structure. Route-specific query representations are deferred until the M3 experiment demonstrates a need.

## Implementation evidence

- Focused suite: `python3.12 -m unittest tests.test_retrieval -v` passed 4/4 tests.
- Repository suite: `python3.12 -m unittest discover -s tests -v` passed 36/36 tests.
- Independent review found one initial contract gap: ranks below one were accepted. The implementer added the minimal validation and boundary test; final review found no actionable issue.
- Independent acceptance verification marked every criterion PASS and confirmed the implementation changed only the two allowed source/test files.

## Approval record

Approved through the user's explicit instruction to start M3 on `2026-09-22`.
