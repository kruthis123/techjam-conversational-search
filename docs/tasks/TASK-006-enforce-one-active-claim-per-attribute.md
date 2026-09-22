# TASK-006: Enforce one active claim per attribute

- Status: `Verified`
- Owner: `implementer`
- Roadmap milestone: `M2 — Deterministic intent and conversational state`
- Related accepted ADRs: `ADR-006`

## Goal

Apply the user's M2 experiment decision so current active intent contains at most one claim per attribute and an intent override changes only its matching attribute.

## Inputs and outputs

Inputs: parsed simulator messages and existing per-session active claims.

Outputs: one claim per active attribute, with unrelated attributes preserved across ordinary updates, indifference, and override.

## Allowed files

- `starter/intent.py`
- `starter/session_state.py`
- `tests/test_intent.py`
- `tests/test_session_state.py`

## Non-goals

- No nested multi-value claim type, event log, superseded-claim store, Agent integration, search state, catalog comparison, or general NLP.
- No change to the user's selected preferred stance or unresolved-turn behavior.

## Acceptance criteria

- Given a semicolon-separated attribute reply, when parsing runs, then one preferred claim preserves its full value text.
- Given any new claim for an already-active attribute, when state updates, then the old claim is replaced and no duplicate attribute remains.
- Given indifference, when state updates, then it remains the single active claim for that attribute.
- Given an intent override, when state updates, then only the matching attribute is replaced and unrelated preferred or required claims remain active.
- Given an unresolved consumed turn, when state updates, then raw and unresolved history still record it while active intent remains unchanged.
- Given the repository test suite, when verification runs, then existing and focused tests pass.

## Test cases

- Semicolon-separated reply produces one claim.
- Ordinary same-attribute replacement.
- Indifference remains one claim.
- Material override preserves a separate preferred color claim and required category claim.
- Existing unresolved-turn behavior remains unchanged.

## Verification commands

```bash
python3.12 -m unittest tests.test_intent tests.test_session_state -v
python3.12 -m unittest discover -s tests -v
```

## Risks or assumptions

- Keeping semicolon-separated values as one string is the smallest lossless representation for the current simulator. A structured multi-value field is deferred until a downstream capability demonstrates a need.

## Implementation evidence

- Focused parser and state suite: `python3.12 -m unittest tests.test_intent tests.test_session_state -v` passed 14/14 tests.
- Repository regression suite: `python3.12 -m unittest discover -s tests -v` passed 32/32 tests.
- Repository scan found no remaining `replace_preferences` reference.

## Review findings and resolution

The first review found one low-priority stale `replace_preferences` flag that communicated the rejected global replacement behavior. The implementer removed the field and its test expectation. Final independent review found no actionable issue, and final acceptance verification marked every criterion PASS on `2026-09-22`.

## Approval record

Approved by the user's explicit M2 experiment decisions on `2026-09-22`.
