# ADR-001: Contract and end-to-end responsibility

- Status: `Superseded before proposal`
- Author: `User`
- Date: `2026-09-15`
- Decision area: `AD-01`
- Related learning cards: `LC-00`, `LC-02`, `LC-14`
- Official requirement references: `docs/competition_specification.md`, `docs/agent_api_contract.json`, `docs/evaluation_config.json`, `docs/submission_rules.md`

## Decision question

How will the system coordinate the lifecycle from `reset` or a turn request to one contract-valid response, and where will end-to-end responsibility for that response reside?

## Supersession note

The user rejected this decision area's level of detail before making or accepting a proposal. It focused on software control flow, validation placement, and failure signaling rather than the desired agent system-design learning. No decision in this record is accepted. The ARCHITECTING workflow now begins with `SD-01` and uses system-design records.

## Scope and non-goals

In scope:

- the outer lifecycle for `reset` and `respond`;
- responsibility for session isolation and turn coordination;
- responsibility for final response validity;
- how failures cross the outer boundary;
- the top-level information flow and test seam.

Not decided here:

- intent representation;
- state representation or storage technology;
- retrieval, constraint, ranking, clarification, personalization, or fallback policy;
- model, framework, dependency, or deployment choices;
- internal interfaces belonging to later decision areas.

## Contract facts and existing decisions

Official facts:

- The evaluator calls `reset(session_id, user_profile)` before the simulated conversation.
- Every turn calls `respond(session_id, user_message, turn, top_k)`, where `turn` is 1 through 10 and `top_k` is 10.
- A response requires `message`, `ask_attribute`, and ordered `recommendations`; `usage` is conditionally optional under the official contract.
- `ask_attribute` must be one allowed value or `null`.
- Recommendation entries require a non-empty `parent_asin`; the response schema permits at most 100 entries, while only the first 10 valid unique IDs are scored.
- Invalid output, exceptions, and timeouts may count as misses.
- The session normally ends after a qualifying hit or turn 10; Intent Override cannot convert before the replacement intent is sent.
- Network access may be disabled, and the submission must be reproducible from declared contents and setup instructions.

Existing architecture decisions: none.

Assumptions that are not official facts:

- whether the evaluator continues or ends a session after each particular exception or invalid response;
- exact CPU, memory, and timeout limits;
- whether reset can be repeated for the same session identifier;
- the internal organization used to coordinate a turn.

## Inputs, outputs, ownership, and invariants

Known external inputs:

- reset: `session_id`, aggregate `user_profile`;
- turn: `session_id`, `user_message`, `turn`, `top_k`.

Required external output:

- one response object conforming to the official response schema.

Ownership questions remain open. Candidate invariants to confirm include:

- state from one session never affects another session;
- every successful return from `respond` is schema-valid;
- the final customer-facing message and `ask_attribute` do not disagree;
- recommendation order is preserved and recommendation IDs come from the frozen catalog;
- a failure has defined, observable behavior rather than leaking malformed output;
- exactly one responsibility is accountable for the final response even if work is delegated internally.

The user's initial ownership position distinguishes two levels:

- each capability owns delivery of its local contract;
- a separate control owner receives failures, decides whether processing can continue without that capability's result, and owns final outer-boundary validation.

This is a position to compare against the solution families, not yet an accepted architecture decision.

## Failure cases

- reset receives invalid or incomplete input;
- respond refers to an unknown or mismatched session;
- turn information is invalid or inconsistent;
- an internal capability fails, times out, or returns unusable information;
- response construction produces an invalid field, duplicate ID, invalid ID, or excessive recommendations;
- natural-language prose and `ask_attribute` request different attributes;
- stale state from another session affects the current turn;
- the system exceeds an unspecified operational limit.

## What I need to research

- Questions I must answer:
  - What does end-to-end ownership mean when several capabilities contribute to one turn?
  - Which responsibility should control sequencing and final validation?
  - Which failures should produce a safe valid response, and which cannot be recovered within the contract?
  - Which minimum trace is needed to explain one turn without exposing private evaluator information?
  - Which responsibilities belong at the outer boundary versus later decision areas?
- Solution families to understand:
  - one coordinating responsibility around delegated capabilities;
  - an explicit sequential pipeline with defined stage contracts;
  - an event/state-machine style controller for multi-turn and failure transitions;
  - distributed coordination in which capabilities share lifecycle responsibility.
- Sources or evidence needed:
  - official API schema, session protocol, output rules, and submission constraints;
  - completed LC-00, LC-02, and LC-14 conclusions;
  - paper walkthroughs of Buying, Browsing, Intent Override, Boundary, and internal-failure scenarios;
  - experiments only if a concrete framework or performance claim is later introduced.

## Decision criteria

The user confirmed that all of these criteria are mandatory:

- contract correctness and session isolation are mandatory;
- ownership of sequencing, failure handling, and final validity is unambiguous;
- hard requirements and other meaning can cross later boundaries without silent reinterpretation;
- important paths can be tested with fixed inputs and fake capability results;
- failures are contained and observable;
- the design remains understandable and no more complex than justified;
- it leaves later decision areas open rather than deciding them implicitly.

## Options I considered

The initial research showed that accountability and flow representation are separate dimensions. The user's current position favors one control owner with locally responsible capabilities, so the useful comparison is how that control owner should represent and execute the flow.

| Option | How it works | Strengths | Failure modes and trade-offs | Evidence |
|---|---|---|---|---|
| Fix ownership now; defer flow representation | This ADR assigns local capability contracts, one control owner, and one final-validation boundary without choosing direct sequencing, a pipeline, or a state machine yet. | Avoids deciding structure before later behavior and state decisions are understood. | Provides less implementation guidance now; requires an explicit later decision and revisit trigger. | Compatibility with later decision areas must be checked. |
| Control owner with direct sequencing | One owner calls capabilities and uses explicit branches to continue, stop internal processing, or construct a response. | Clear accountability; low conceptual overhead; direct failure routing. | The owner can accumulate policy details or become difficult to change if branching grows. | Paper scenario trace pending. |
| Control owner with an explicit pipeline | One owner passes a turn through ordered stages with defined stage contracts and performs final validation. | Clear transformations and test seams; local capability contracts remain visible. | Overrides, clarification loops, optional stages, and failures require explicit branching outside a purely linear pipeline. | Paper scenario trace pending. |
| Control owner with a state-machine/workflow representation | One owner advances explicit states or transitions based on results and failures. | Lifecycle and exceptional transitions are explicit; useful when many non-linear paths exist. | More concepts and transition definitions; may be unjustified if the flow is mostly simple. | Paper scenario trace pending. |
| Distributed coordination | Capabilities decide or signal what executes next, sharing lifecycle control. | Flexible local composition. | Conflicts with the user's goal of one consistent failure decision owner; fragmented final accountability and harder end-to-end tests. | Conceptual conflict with confirmed mandatory criteria; no experiment needed to establish that conflict. |

Failure communication is another interface choice that remains unresolved:

| Family | Meaning | Trade-off |
|---|---|---|
| Exceptions only | Any inability to deliver the local contract interrupts normal flow. | Simple, but expected absence, recoverable failure, and defects can become difficult to distinguish. |
| Structured result only | Every capability returns success or a defined failure value with context. | Explicit and testable, but unexpected programming defects can be accidentally treated as routine outcomes. |
| Structured expected failures plus exceptions for unexpected defects | Recoverable or expected inability is represented in the local contract; unexpected defects interrupt it. | Preserves the distinction, but requires the boundary between expected and unexpected failure to be defined. |

## Validation experiments

No code experiment is currently required. First use a paper scenario trace with fixed inputs to determine whether each option provides unambiguous ownership, valid failure behavior, and a testable final-output boundary.

If the user later proposes a framework, concurrency model, or latency claim, define a separate smallest experiment before relying on that claim.

## Questions I must answer before deciding

Initial user answers:

1. "No, one capability is only responsible to deliver its contract if it fails then there is another owner who receives the failure and decides whether we need to terminate now or can we proceed without the processed information from this capability. This ensures there is no repeated failure decision making at each node which can also lead to differences in handling"
2. "Final validation at one outer boundary. Individual capabilities are responsible for resolving their contracts"
3. "Outer boundary can decide whether the flow can continue or an error/default response must be returned"
4. "All are mandatory"

Contract clarification from the facilitator:

- The control owner may stop internal processing, continue without a result, return a valid ordinary response, or allow an exception according to the eventual failure policy. It cannot directly terminate the evaluator-managed session.
- The official schema defines no special error-response shape. Any default returned to the evaluator must still be an ordinary schema-valid turn response; an exception, invalid output, or timeout may become a miss.

Questions still requiring an answer before proposal:

1. Which solution family, or explicit combination, best supports local capability ownership plus one control owner?
2. What responsibilities belong to the control owner, and which responsibilities must it not absorb?
3. What common failure information must every capability provide to the control owner?
4. Should the outer guarantee be best-effort delivery of a valid ordinary response before the deadline, or may some named failures deliberately escape as exceptions?

## My proposed decision

Awaiting the user's proposal after research and comparison.

## Architecture critic feedback

- What is clear and testable: awaiting proposal.
- Blocking questions: awaiting proposal.
- Unresolved trade-offs: awaiting proposal.
- Required experiments: awaiting proposal.

## My final decision

Not accepted.

## Why I chose it and evidence used

Not written.

## Rejected alternatives and why

Not written.

## Consequences and trade-offs I accept

Not written.

## Interfaces or invariants this decision creates

Not written.

## Compatibility check

- Official contract: pending.
- Previously accepted ADRs: none.
- Buying scenario: pending.
- Browsing scenario: pending.
- Intent Override scenario: pending.
- Boundary scenario: pending.
- Operational failure: pending.

## Revisit trigger

Not written.
