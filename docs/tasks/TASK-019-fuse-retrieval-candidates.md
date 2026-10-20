# TASK-019: Fuse retrieval candidates

- Status: `Verified`
- Owner: `implementer`
- Roadmap milestone: `M4 — Candidate fusion and constraint-aware selection`
- Related accepted ADRs: `ADR-009`, `ADR-010`

## Goal

Combine independent retrieval-route results into one deterministic,
deduplicated RRF order while retaining every contributing route's evidence.

## Inputs and outputs

Input: route names mapped to their ordered `RetrievalHit` results.

Output: ordered fused candidates containing `parent_asin`, RRF score, and the
contributing route name, local rank, and local score.

## Allowed files

- `starter/fusion.py`
- `tests/test_fusion.py`
- `docs/tasks/TASK-019-fuse-retrieval-candidates.md`
- `docs/PROJECT_STATE.md`

## Non-goals

- Running retrieval routes.
- Applying a candidate cutoff.
- Checking constraints or assigning eligibility.
- Final recommendation ranking.
- Comparing alternative fusion formulas or rank constants.

## Acceptance criteria

- Given the same product from multiple routes, when results are fused, then it
  appears once and its RRF score includes every contributing route rank.
- Given fused candidates with different RRF support, when they are ordered,
  then higher RRF scores appear first.
- Given equal RRF scores, when candidates are ordered, then `parent_asin`
  provides a deterministic tie-breaker.
- Given a fused candidate, when its evidence is inspected, then each
  contributing route's name, local rank, and local score are preserved.
- Given no route hits, when results are fused, then the output is empty.

## Test cases

- A product shared by BM25 and facet plus a product returned only by SVD-256.
- Two products with equal route ranks to verify the identity tie-breaker.
- Empty route results.

## Verification commands

```bash
unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest tests.test_fusion -v
unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest discover -v
```

## Risks or assumptions

- Existing retrievers already return one hit per product per route with
  one-based ranks.
- The RRF rank constant is the baseline recorded in `ADR-010`; tuning it is not
  part of this task.

## Approval record

Approved under the user's explicit instruction to proceed to M4 on
`2026-09-28`.

## Implementation evidence

- Candidate union and accumulated RRF support: `test_deduplicates_candidates_and_combines_route_support`
  verifies that a shared product appears once and receives contributions from
  both route-local ranks.
- Descending RRF order: the same test verifies that the multiply supported
  candidate precedes the two single-route candidates and that rank 1 precedes
  rank 2 among single-route candidates.
- Deterministic tie-breaking: `test_uses_parent_asin_to_break_equal_score_ties`
  verifies identity ordering for equal single-route support, and
  `test_equal_rank_multisets_tie_across_route_permutations` verifies the same
  behavior for equal rank multisets accumulated in different orders.
- Preserved route evidence: `test_deduplicates_candidates_and_combines_route_support`
  verifies each contributing route name, local rank, and local score.
- Empty input behavior: `test_returns_empty_tuple_when_routes_have_no_hits`
  verifies an empty tuple is returned.
- Focused verification passed 4/4 tests:
  `unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest tests.test_fusion -v`.
- Independent focused verification passed 4/4 tests.
- Full repository verification passed 74/74 tests:
  `unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest discover -v`.

## Review findings and resolution

- Resolved: ordinary `sum` could produce different floating-point values for
  the same rank multiset accumulated in different route orders, preventing the
  `parent_asin` tie-break from applying. RRF contributions now use
  order-independent accurate `math.fsum`, with a focused permutation
  regression test. The focused suite passes 4/4 tests after the fix.
- Independent re-review found no remaining high- or medium-priority findings.
- The `docs/IMPLEMENTATION_ROADMAP.md` status change belongs to the M4 planning
  and activation step that preceded this task; it was not an implementation
  change made by TASK-019.
