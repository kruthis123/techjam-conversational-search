# SDR-003: Conversational memory and preference evolution

- Status: `Synthesized`
- Author: `User`
- Date: `2026-09-16`
- System-design area: `SD-03`
- Related learning cards: `LC-02`, `LC-07`, `LC-09`
- Case-study references: `docs/competition_specification.md`, `docs/agent_api_contract.json`

## System question

What should the agent remember across turns, and how should additions, refinements, corrections, exclusions, indifference, ambiguity, and reset change the user's current intent?

## Why this capability matters

`SD-02` produces grounded claims about the current message. A conversational agent must combine those turn-level claims with earlier evidence without retaining stale preferences or deleting unrelated requirements. Retrieval, filtering, ranking, and dialogue policy need a trustworthy view of current intent plus enough history to explain how that view arose.

## Information available

- raw user and agent messages by turn;
- turn-level observed claims and optional inferred claims from `SD-02`;
- the attribute the agent asked about and the user's reply;
- prior active, superseded, excluded, indifferent, unknown, and unresolved claims;
- source turn, evidence, provenance, confidence, and update operation;
- session reset as the boundary for conversation-specific memory;
- aggregate user profile as a separate historical prior, studied in `SD-08`.

## Useful representations

Potential memory views include:

- complete turn history for evidence and replay;
- an event sequence of claim additions, updates, cancellations, exclusions, and indifference;
- a current active-intent view derived from those events;
- unresolved conflicts or alternative interpretations;
- a compact summary for reasoning or prompting;
- derived search state such as rewritten queries or candidate sets, whose invalidation is a later orchestration concern.

Important claim states include active, superseded, cancelled, excluded, indifferent, unknown, inferred, and unresolved. These states are not interchangeable.

## Solution families to learn

- replay the full conversation on every turn;
- maintain only a mutable current-state snapshot;
- preserve an append-only sequence of semantic events;
- compress history into a natural-language or structured summary;
- combine durable events with a materialized current-intent view;
- deterministic update operations versus learned dialogue-state tracking;
- confidence decay, conflict sets, or clarification for ambiguous revisions.

## What I need to research

- Concepts and vocabulary: dialogue state tracking, belief state, event, snapshot, carryover, update, delete, replace, indifference, conflict, provenance, replay, summary drift, selective invalidation.
- Algorithms or system patterns: slot carryover, operation prediction, event-derived state, structured summaries, learned state tracking, and conflict-aware updates.
- Questions the research must answer:
  - Which information is needed for current decisions, and which is needed only for audit or recovery?
  - Should superseded evidence be deleted, retained as history, or represented in both forms?
  - How are unrelated requirements preserved during a correction?
  - How are ambiguous updates represented without choosing prematurely?
  - When can memory be compressed without losing preference strength, provenance, or cancellation history?

## Comparison criteria

To be confirmed by the user. Candidate criteria include correctness of current intent, selective update accuracy, resistance to stale-state influence, explainability, recoverability, memory growth, summary drift, deterministic behavior, and ease of testing on simulator trajectories.

## Study sequence

1. Distinguish raw dialogue history, semantic events, current intent, and derived search state.
2. Compare full-history replay, current snapshot, event history, summary, and hybrid memory views.
3. Define conceptual update operations for carryover, add, refine, replace, exclude, remove, indifference, and unresolved conflict.
4. Trace Buying, Browsing, Intent Override, and Boundary examples through those operations.
5. Record the user's memory strategy and the evidence needed before introducing learned state tracking.

## Research evidence

- Selective-overwrite dialogue state tracking models state changes as carryover, delete, indifference, and update operations: https://aclanthology.org/2020.acl-main.53/
- TripPy illustrates copying values from current utterances, prior system information, and existing dialogue state: https://aclanthology.org/2020.sigdial-1.4/
- Research comparing context granularity distinguishes rebuilding state from full history from updating previous state with the current turn: https://aclanthology.org/2021.acl-long.193/

## Worked example or thought experiment

| Turn | User message | Intended effect |
|---|---|---|
| 1 | "I need a backpack under $100. Leather would be nice." | Add product need and budget requirement; add soft leather preference. |
| 2 | "It must fit a 15-inch laptop." | Add laptop requirement; preserve budget and leather preference. |
| 3 | "Actually, no leather. Nylon only." | Supersede the positive leather preference, exclude leather, add hard nylon requirement; preserve budget and laptop requirement. |
| 4 | "I have no color preference." | Establish color indifference; preserve unrelated active claims. |

The exercise will compare what each memory representation stores and what current intent it exposes after every turn.

### User's first exercise answers

1. "derived search state"
2. "retain for audit"
3. "Here \"nylon instead\" means replace leather with nylon along with the same user stance that was attached to leather. The operation must be determined based on the simulator's template"

### Facilitator feedback

- Derived search state is downstream of conversational memory rather than a sufficient memory source. A cached query or candidate list does not reliably preserve whether leather was required, preferred, inferred, or excluded, and it cannot support the requested audit trail by itself.
- Retaining superseded claims as inactive historical evidence supports audit, correction, and replay. They must no longer influence the current intent or derived search state.
- Under the user's closed-world simulator scope, a known "X instead" template may deterministically replace the earlier value and carry its stance when the template defines that meaning. The template must define whether hedging such as "I guess" changes strength; stance inheritance should not be assumed for unrestricted natural language.
- A semantic change signal should identify which derived queries, candidates, filters, boosts, or penalties may now be stale. The specific invalidation behavior belongs to later retrieval, ranking, and orchestration areas.

### User's initial memory-view refinement

The user accepted:

1. retaining raw messages, semantic events, and current active intent as conversational memory while keeping derived search state as a separate downstream working view;
2. omitting a natural-language summary for the current ten-turn, template-controlled simulator;
3. preserving unmatched or ambiguous updates as unresolved rather than changing active intent, and surfacing those cases for investigation.

### User revision after synthesis

The user subsequently removed the semantic-event-history and superseded-claim requirements. For the bounded, deterministic simulator, the selected memory views are now:

- raw message history as the evidence and replay source;
- structured dialogue context in the turn history, including the emitted `ask_attribute` and the next reply linked to it;
- a mutable current active-intent view;
- unresolved interpretations linked to their raw message and turn;
- derived search state as a separate downstream working view.

Active exclusions remain in current intent because they still constrain the search. Removed or superseded preferences do not remain in current intent and are not copied into a separate semantic event log; their original wording remains available only in raw history. When audit or recovery is needed, the system can deterministically replay the short raw history.

## Learning experiment

Start with a paper state trace over fixed simulator trajectories. For each turn, compare the expected current intent with state reconstructed by full replay, snapshot updates, event replay, and summary-only memory. A later automated experiment is justified if these alternatives remain plausible after conceptual comparison.

## My synthesis

Accepted by the user on `2026-09-16` and revised later that day:

- Retain the raw turn history as the authoritative conversational evidence within a session.
- Preserve each emitted structured `ask_attribute` in its turn record and link it to the next simulator reply. Asked-attribute and answer status may be reconstructed from these records without a separate semantic event log.
- Maintain a mutable current active-intent view for retrieval, filtering, ranking, and dialogue decisions.
- Keep derived queries, candidates, filters, boosts, and penalties as a separate working search view rather than treating them as conversational truth.
- Rebuild the derived search state from the current active intent on every turn. Retrieval, constraint checking, and ranking may progressively populate that turn-local state, but no derived search artifacts are reused across turns initially.
- Do not maintain a separate semantic event log or a separate store of superseded claims. Raw history is sufficient for replay or investigation within the bounded conversation.
- Keep currently active exclusions in the active-intent view. Remove superseded or retracted preferences from that view so they cannot influence retrieval or ranking.
- Under the closed simulator grammar, deterministic templates define update operations. A known "X instead" template replaces the earlier value and inherits its stance when the simulator semantics specify that behavior.
- If a message does not match a known or unambiguous update template, preserve the interpretation as unresolved and do not modify active intent immediately.
- Surface unresolved updates with their raw evidence, source turn, and failure category so the parsing or template-coverage issue can be investigated. Later dialogue-policy design may decide whether clarification is useful.
- A natural-language summary is unnecessary for the current maximum ten-turn, template-controlled conversations because raw evidence and the structured active-intent view remain bounded.
- Reset clears conversation-specific raw history, current intent, unresolved interpretations, and derived search state for the named session before initialization.
- Changes can be detected by comparing the previous and updated active-intent views so later capabilities can invalidate stale derived information. No persistent semantic event is required. Exact invalidation policies belong to later system-design areas.
- Cross-turn caching or selective reuse is deferred until measurement shows that rebuilding causes a meaningful latency or resource problem. Any later cache must be validated against stale-result failures before adoption.

No storage technology or implementation structure has been selected.

## Connections to the rest of the agent

- Information required from upstream capabilities: grounded turn-level claims and update operations from `SD-02`.
- Information supplied to downstream capabilities: current active intent, evidence history, structured question-reply context, and unresolved conflicts. Downstream search capabilities build a fresh derived search state for the current turn.
- New questions created for later areas: which state changes trigger retrieval, filtering, ranking, or dialogue-policy updates, and what historical profile information remains separate.

## Architecture critic feedback

Awaiting user synthesis.

## Revisit conditions

Revisit when later retrieval, ranking, dialogue, or personalization choices require additional memory views or expose summary drift and stale-state failures.
