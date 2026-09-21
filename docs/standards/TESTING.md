# Testing Standard

## Acceptance-to-evidence rule

Every acceptance criterion must map to one of:

- an automated focused test;
- an official evaluator result;
- a deterministic inspection with recorded evidence;
- `NOT VERIFIED` with a precise blocker.

## Required layers as they become relevant

- Contract tests for `reset` and `respond` output.
- Unit tests for deterministic logic.
- Integration tests for boundaries between accepted components.
- Scenario tests for Buying, Browsing, Intent Override, and Boundary behavior.
- Regression evaluation on a development slice that was not used to tune the change.

## Test quality

- Test behavior, not private implementation details.
- Include the important edge and failure paths named in the task.
- For learning-first tasks, start with the main behavior, one meaningful abstention or boundary, and only contract-critical or observed failures. Do not create an exhaustive hypothetical edge-case matrix by default.
- Add a new test when an experiment or real failure teaches something worth preserving.
- Keep tests deterministic and fast enough for the task loop.
- Never weaken a test or edit official evaluation artifacts solely to make a change pass.
- Report the exact command and result; do not summarize a check that was not run.
