# TASK-014: Try one retrieval route at several depths

- Status: `Verified`
- Owner: `implementer`
- Roadmap milestone: `M3 — Baseline catalog representations and retrieval routes`
- Related accepted ADRs: `ADR-007`

## Goal

Provide a disposable command-line script for manually inspecting one retrieval route, one target product, one explicit query, and several candidate depths.

## Inputs and outputs

Inputs: route name, target `parent_asin`, query text, candidate depths, and optional catalog path.

Output: readable JSON showing the route, target, query, and the retrieved IDs, scores, and target rank at each depth.

## Allowed files

- `experiments/try_single_retrieval.py`

## Non-goals

- No unit tests, production API, Agent integration, query generation, evaluator use, comparison automation, tuning decision, or documentation changes.

## Acceptance criteria

- Given `lexical`, `facet`, or `dense`, when the script runs, then it instantiates only that route.
- Given one query and several positive depths, when retrieval runs, then each depth is reported separately with hits and target rank or `null`.
- Given CLI help, when invoked, then the script explains all inputs without loading the catalog.
- Given the script, when verification runs, then it compiles and CLI help exits successfully without running an experiment.

## Verification commands

```bash
unset VIRTUAL_ENV && uv run --python 3.12 python -m py_compile experiments/try_single_retrieval.py
unset VIRTUAL_ENV && uv run --python 3.12 python -m experiments.try_single_retrieval --help
```

## Risks or assumptions

- This is intentionally disposable and has no unit-test coverage. The target identifier is diagnostic only and does not alter retrieval.

## Implementation evidence

- Static review confirmed that only the selected route is imported and instantiated, the target ID is diagnostic only, and each depth produces separate hits and a target rank or `null`.
- `unset VIRTUAL_ENV && uv run --python 3.12 python -m py_compile experiments/try_single_retrieval.py` passed.
- `unset VIRTUAL_ENV && uv run --python 3.12 python -m experiments.try_single_retrieval --help` passed without loading the catalog or running retrieval.
- Independent review found no actionable issue. Independent acceptance verification marked every criterion PASS.
- No real retrieval, M3 comparison, or holdout access occurred.

## Review findings and resolution

No actionable findings were reported. Unit tests remain intentionally omitted under the user's throwaway-script instruction.

## Approval record

Approved by the user's explicit request for a rough throwaway script without unit tests on `2026-09-27`.
