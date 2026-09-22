# TASK-005: Maintain current intent per session

- Status: `Verified`
- Owner: `implementer`
- Roadmap milestone: `M2 — Deterministic intent and conversational state`
- Related accepted ADRs: `ADR-006`

## Goal

Maintain raw turn history, question-reply links, unresolved messages, and current active intent independently for each reset session.

## Inputs and outputs

Inputs: `session_id`, turn number, raw user message, and the `ask_attribute` emitted before the next user reply.

Output: the current session state containing ordered turn records, active claims, unresolved turn records, and any pending question attribute.

## Allowed files

- `starter/session_state.py`
- `tests/test_session_state.py`

## Non-goals

- No Agent integration, search state, persistence, semantic event log, superseded-claim archive, summary, profile use, concurrency, or recovery behavior.
- No changes to message parsing or catalog claims.

## Acceptance criteria

- Given a reset session, when messages are received, then raw messages and their turn numbers are preserved in order.
- Given a recorded `ask_attribute`, when the next message arrives, then its turn record links to that attribute and the pending question is cleared.
- Given ordinary claims, when they are applied, then distinct active claims accumulate without exact duplicates.
- Given an indifferent claim, when it is applied, then earlier active claims for that attribute are replaced by indifference.
- Given the override update, when it is applied, then earlier preferred claims are removed while unrelated required claims remain active.
- Given an unresolved message, when it is received, then active intent remains unchanged and the raw turn is retained for investigation.
- Given two sessions and a reset, when state changes occur, then sessions remain isolated and resetting one clears only that session.
- Given the repository test suite, when verification runs, then existing and focused tests pass.

## Test cases

- Question reply and accumulated claims.
- Indifference replacement.
- Intent override preserving category.
- Unresolved message with unchanged intent.
- Two-session isolation and reset.

## Verification commands

```bash
python3.12 -m unittest tests.test_session_state -v
python3.12 -m unittest discover -s tests -v
```

## Risks or assumptions

- One pending question is sufficient because the public contract permits one `ask_attribute` per response.
- The store is intentionally in-memory and single-process for this learning project.

## Implementation evidence

- Focused state suite: `python3.12 -m unittest tests.test_session_state -v` passed 5/5 tests.
- Repository regression suite: `python3.12 -m unittest discover -s tests -v` passed 31/31 tests.

## Review findings and resolution

Independent review found no actionable issue, scope creep, or unnecessary complexity. Independent acceptance verification marked every criterion PASS on `2026-09-21`.

## Approval record

Approved through the user's explicit instruction to start M2 on `2026-09-21`, after TASK-004 verification.
