# TASK-004: Parse simulator messages into intent updates

- Status: `Verified`
- Owner: `implementer`
- Roadmap milestone: `M2 — Deterministic intent and conversational state`
- Related accepted ADRs: `ADR-006`

## Goal

Convert one known simulator message into a small deterministic intent update without consulting catalog products or previous active intent.

## Inputs and outputs

Input: one raw user message and an optional prior `ask_attribute`.

Output: an immutable parse result containing ordered observed claims, whether earlier preferences must be replaced, and whether the message is unresolved.

## Allowed files

- `starter/intent.py`
- `tests/test_intent.py`

## Non-goals

- No session storage, state mutation, Agent integration, catalog lookup, inference, confidence, general NLP, or paraphrase handling.
- No hidden-intent-card access.
- No exhaustive malformed-message handling.

## Acceptance criteria

- Given buying, browsing, and intent-override initial templates, when parsing runs, then category and disclosed values receive the stance defined in ADR-006.
- Given attribute-information and no-preference replies linked to an `ask_attribute`, when parsing runs, then preferred or indifferent claims are emitted for that attribute.
- Given the override template, when parsing runs, then it emits a required replacement claim and marks earlier preferences for replacement.
- Given a bare reply linked to an `ask_attribute`, when parsing runs, then it emits one preferred claim for that attribute.
- Given an unknown message without a question link, when parsing runs, then it is unresolved and emits no claim.
- Given the repository test suite, when verification runs, then existing and focused tests pass.

## Test cases

- One compact test for each simulator template family.
- One bare linked reply.
- One unknown unlinked message.

## Verification commands

```bash
python3.12 -m unittest tests.test_intent -v
python3.12 -m unittest discover -s tests -v
```

## Risks or assumptions

- The baseline deliberately learns the evaluator's closed grammar rather than general language understanding.
- `what matters is` remains preferred because its wording does not expose hidden hard-versus-soft labels.

## Implementation evidence

- Focused parser suite: `python3.12 -m unittest tests.test_intent -v` passed 8/8 tests.
- Repository regression suite: `python3.12 -m unittest discover -s tests -v` passed 26/26 tests.

## Review findings and resolution

Independent review found no actionable issue, unsupported-claim risk, scope creep, or unnecessary complexity. Independent acceptance verification marked every criterion PASS on `2026-09-21`.

## Approval record

Approved through the user's explicit instruction to start M2 on `2026-09-21`.
