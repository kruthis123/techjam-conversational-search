# TASK-012: Record retrieval queries in M3 results

- Status: `Verified`
- Owner: `implementer`
- Roadmap milestone: `M3 — Baseline catalog representations and retrieval routes`
- Related accepted ADRs: `ADR-007`

## Goal

Make the exact message-derived query used for each session visible in the M3 comparison JSON so retrieval failures can be interpreted.

## Inputs and outputs

Input: each selected public session and the single query already shared by the lexical, facet, and dense routes.

Output: a `queries_by_sample_id` mapping for every evaluated session and the same query beside each representative miss.

## Allowed files

- `experiments/m3_compare_routes.py`
- `tests/test_m3_compare_routes.py`
- `docs/experiments/M3-retrieval-route-comparison.md`

## Non-goals

- No query change, query expansion, additional retrieval call, route-specific query, new metric, full experiment execution, or holdout access.
- No target identifier or target product content may be added to a query.

## Acceptance criteria

- Given an evaluated session, when route execution runs, then its exact shared query is recorded once under its sample ID.
- Given representative misses, when result summarization runs, then every miss includes the query used by all three routes for that session.
- Given recorded queries, when inspected, then they do not change the query or depth passed to any route.
- Given the result schema, when the experiment guide is read, then it explains where to inspect all queries and miss-local queries.
- Given the focused and repository suites, when verification runs, then they pass without executing the full-catalog experiment.

## Test cases

- Route execution returns the expected sample-to-query mapping while preserving identical route calls.
- Synthetic miss output contains the expected query.
- Existing split, metrics, and CLI tests remain unchanged.

## Verification commands

```bash
unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest tests.test_m3_compare_routes -v
unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest discover -s tests -v
```

## Risks or assumptions

- The three M3 routes intentionally share one query, so storing one value per session is clearer than duplicating it three times.

## Implementation evidence

- `execute_routes` records the exact shared query under each evaluated sample ID and passes the same query and depth to all three routes.
- `summarize_results` exposes `queries_by_sample_id` and copies the matching query into every representative miss.
- The experiment guide documents both query-inspection locations.
- Focused locked-environment suite: `unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest tests.test_m3_compare_routes -v` passed 5/5 tests.
- Repository locked-environment suite: `unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest discover -s tests -v` passed 53/53 tests.
- Independent review found no actionable issue. Independent acceptance verification marked every criterion PASS.
- The full comparison was not run and holdout results were not accessed.

## Review findings and resolution

No actionable findings remained after independent review and verification.

## Approval record

Approved by the user's explicit request to include the query used for each retrieval result on `2026-09-27`, within the existing M3 authorization.
