# TASK-011: Prepare the M3 retrieval comparison runner

- Status: `Verified`
- Owner: `implementer`
- Roadmap milestone: `M3 — Baseline catalog representations and retrieval routes`
- Related accepted ADRs: `ADR-007`

## Goal

Prepare, but do not execute, one reproducible command that compares the three verified routes on identical first-turn public-session queries.

## Inputs and outputs

Inputs: the frozen catalog, public labeled sessions, a fixed tuning/holdout selection, and one candidate depth shared by every route.

Output: JSON evidence containing route Recall@K, union recall, unique target contribution, pairwise candidate overlap, build/search latency, scenario and difficulty slices, and representative misses.

## Allowed files

- `experiments/m3_compare_routes.py`
- `tests/test_m3_compare_routes.py`

## Non-goals

- Do not run the full-catalog comparison during implementation or verification.
- No Agent integration, dialogue replay beyond the first simulator message, route fusion, RRF, filtering, final ranking, threshold tuning, holdout interpretation, or automatic keep/change/defer decision.
- No target identifier or target product record may enter route construction or search. The official evaluator may use the public label inside its existing materialization boundary to reconstruct the simulator's first customer message; retrieval receives only the resulting parsed query. Labels are otherwise used only after retrieval to calculate experiment evidence.

## Acceptance criteria

- Given the 200 public sessions, when deterministic scenario-stratified selection runs, then 160 tuning and 40 holdout sessions are produced with no overlap and with the 80/20 scenario proportions preserved.
- Given a session, when its experiment query is built, then the official evaluator materializes the same first simulator message, which is parsed through M2 and converted through TASK-007; neither the target identifier nor its product record is passed to any retrieval route.
- Given one requested depth, when comparison runs, then lexical, facet, and dense routes all receive the same query and depth.
- Given route outputs, when summarization runs, then it reports per-route Recall@K, union recall, unique target contribution, mean pairwise Jaccard overlap, build time, mean and p95 search time, scenario/difficulty recall counts, and bounded miss examples.
- Given `--split tuning` or `--split holdout`, when the command runs, then only the selected session IDs are evaluated and the chosen split is named in the JSON.
- Given the runner, when focused tests and the repository suite run, then they pass without executing the full-catalog experiment.

## Test cases

- Deterministic stratified split counts, scenario counts, and no overlap.
- Synthetic route results with known recall, union, unique contribution, overlap, slices, and misses.
- CLI help proves required split/depth inputs without loading the catalog.

## Verification commands

```bash
unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest tests.test_m3_compare_routes -v
unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest discover -s tests -v
```

## Risks or assumptions

- This is a first-turn retrieval experiment because later dialogue policy is not implemented yet. It isolates M3 candidate coverage rather than claiming end-to-end agent quality.
- The holdout command exists for a later user-approved milestone check; routine inspection starts with tuning only.
- The released public sessions omit the hidden intent card and behavior. Reconstructing the official first message therefore uses the public target inside the evaluator's simulator-materialization boundary. This does not expose the target to runtime retrieval: routes receive only the customer message-derived query, exactly as they would during evaluation.

## Implementation evidence

- Focused locked-environment suite: `unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest tests.test_m3_compare_routes -v` passed 5/5 tests.
- Repository locked-environment suite: `unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest discover -s tests -v` passed 53/53 tests.
- Independent review initially found that the test fixture bypassed public-session materialization. The implementer corrected the fixture; final review found no actionable issue.
- Independent acceptance verification marked every criterion PASS and confirmed the full-catalog comparison was not run.

## Approval record

Approved through the user's explicit instruction to start M3 on `2026-09-22`.
