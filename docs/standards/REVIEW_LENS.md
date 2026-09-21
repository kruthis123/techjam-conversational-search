# User Review Lens

Review through these priorities, in order:

1. Correctness against the active acceptance criteria.
2. Compliance with the official agent and scoring contract.
3. Adherence to accepted user architecture.
4. Generalization beyond the 200 public sessions.
5. Clear state, data ownership, failure behavior, and meaningful tests.
6. Simplicity and maintainability under the user's approved style.

## User-approved review heuristics

### Flag unnecessary complexity in learning tasks

- Heuristic: Reviewers should challenge code, data fields, validation branches, and tests that are not required by the active learning behavior or current evidence.
- Evidence that triggered it: The user explicitly prioritized a very small, readable implementation and learning through later experiments over resolving every possible edge case.
- What reviewers should flag: speculative abstractions, production hardening, duplicated representations, broad error matrices, and code that makes the current concept harder to understand without measured benefit.
- What reviewers should not flag: intentionally deferred hypothetical edge cases that are documented, do not violate the official contract for current inputs, and have not appeared in the fixed data or current experiment.
- Date approved: `2026-09-18`

### Preserve the experiment handoff

- Heuristic: Reviewers should distinguish deterministic implementation verification from experiments that compare alternatives. Codex may run the former, but the latter must end in a reproducible handoff for the user.
- What reviewers should flag: silently selecting an experimental winner, tuning several factors together, implementing deferred alternatives before evidence, or giving an experiment without fixed inputs and a clear decision question.
- What reviewers should not flag: autonomous local implementation decisions that stay within the authorized milestone and keep the code smaller.
- Date approved: `2026-09-18`

## Feedback ledger

Record important reviewer suggestions as `Accepted`, `Rejected`, or `Needs evidence` so future agents learn the user's judgment rather than repeating generic advice.
