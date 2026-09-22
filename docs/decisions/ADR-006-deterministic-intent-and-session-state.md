# ADR-006: Minimal deterministic intent and session state

- Status: `Accepted under M2 authorization`
- Author: `Codex under user-delegated implementation authority`
- Date: `2026-09-21`
- Decision area: `M2 deterministic intent and conversational state`
- Related system-design records: `SDR-002`, `SDR-003`, `SDR-012`

## Decision question

What is the smallest representation and update policy that preserves the meaning exposed by the repository's deterministic simulator templates?

## Evidence and boundaries

The simulator emits a closed set of message shapes for initial category requests, one explicit key requirement, exploratory requests, attribute replies, indifference, and intent override. General paraphrase handling is outside the accepted project scope.

M1 provides product-side price and category claims. M2 handles user-side claims only and does not compare them with products.

## Options considered

| Option | Benefit | Cost | Decision |
| --- | --- | --- | --- |
| Unstructured accumulated query text | Very small | Cannot represent indifference, replacement, or question links reliably | Rejected |
| Fixed dictionary with one scalar value per attribute | Easy lookup | Awkward for the simulator's semicolon-separated values | Rejected |
| Small attribute-keyed claim list plus raw turn history | Preserves stance and source message while keeping one current meaning per attribute | Multi-value replies must remain one textual value | Selected |

## Final decision

- Represent an observed user claim with only `attribute`, `value`, and `stance`.
- Use the stances `required`, `preferred`, and `indifferent`. Absence remains unknown and is not stored as a claim.
- Parse only the actual simulator templates plus a bare reply linked to a prior `ask_attribute`.
- Treat `A key requirement is` and `What I need is` as required.
- Treat `what matters is` and a bare linked reply as preferred because those templates do not explicitly say `must`.
- Store the requested product category as required.
- Classify a constraint into the simulator's allowed attribute vocabulary with small deterministic keyword rules and `feature` as the fallback.
- Store raw turn history with the prior `ask_attribute` that the message answers.
- Keep at most one active claim per attribute. A new claim replaces the current claim for that attribute.
- Preserve a semicolon-separated attribute reply as one textual claim instead of creating several claims with the same attribute.
- Indifference removes active claims for that attribute and leaves one indifferent claim.
- The override template replaces only the active claim for the changed attribute. Claims for every other attribute remain active regardless of stance.
- Unknown unlinked messages are retained as unresolved and do not change active intent.
- Keep one independent state per `session_id`; reset replaces that session's history and active intent.

## Explicit non-goals

- No LLM, supervised model, generic NLP pipeline, confidence score, semantic event log, natural-language summary, inferred claims, search state, Agent integration, or persistence.
- No general paraphrase support or production error recovery.
- No product eligibility or retrieval behavior.

## Revisit trigger

Revisit only when the M2 trace experiment exposes an incorrect template interpretation or a later capability requires information absent from this representation.

## Authorization record

Selected under the user's explicit `start with M2` instruction on `2026-09-21`. Experimental interpretation choices remain subject to the user's M2 trace decision.

## M2 experiment result

Recorded from the user's trace review on `2026-09-22`:

- Keep attribute-information replies as preferred.
- Enforce one active claim per attribute; indifference replaces the previous claim for that attribute.
- Override only the changed attribute rather than removing every preferred claim.
- If an unresolved message consumed a turn, retain it in raw and unresolved history without changing active intent.

The initial implementation already satisfied indifference and unresolved-turn handling. It allowed multiple active claims for one attribute and removed every preferred claim during override, so those two behaviors require a focused correction.
