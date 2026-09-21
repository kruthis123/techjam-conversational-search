# SDR-012: End-to-end conceptual agent

- Status: `Synthesized`
- Author: `User`
- Date: `2026-09-17`
- System-design area: `SD-12`
- Related learning cards: `LC-00` through `LC-14`
- Case-study references: `docs/competition_specification.md`, `docs/agent_api_contract.json`, `docs/evaluation_config.json`, `docs/submission_rules.md`
- Prior system-design records: `SDR-001` through `SDR-011`

## System question

How do the selected catalog, intent, memory, retrieval, constraint, ranking, dialogue, personalization, orchestration, response, and evaluation decisions form one coherent conceptual agent without losing meaning or creating contradictory responsibilities at capability boundaries?

## Why this capability matters

Each earlier capability was designed separately. The complete agent succeeds only if catalog provenance, user stance, current intent, candidate identity, uncertainty, exclusion reasons, ranking evidence, question decisions, and failure signals survive every boundary. This area checks the integrated information flow and identifies remaining experimental parameters without adding unapproved implementation structure.

## Selected decision inventory

- `SD-01`: raw catalog fields remain truth; initial searchable views are normalized facets, fielded lexical representation, and single-vector dense embeddings; deterministic multi-view is conditional on measured recall gaps.
- `SD-02`: simulator-scoped deterministic extraction creates grounded open claims; observed extraction is separate from inference; inferred claims cannot create hard exclusions.
- `SD-03`: session memory contains raw message history and mutable current active intent; no semantic event log or superseded-claim store; derived search state is rebuilt every turn.
- `SD-04`: BM25 or fielded lexical, facet, and dense routes run every turn at equal initial depth; RRF fuses and truncates candidates; route depths, cutoff, and advanced retrieval remain experimental.
- `SD-05`: candidates become confirmed, provisional, or ineligible; only reliable contradictions exclude; unknown and inferred evidence remain provisional; hard requirements are never silently relaxed.
- `SD-06`: rank retained candidates with exact lexicographic signal groups and separately normalized within-group weighted scores; relevance precedes retrieval evidence, soft preference, and popularity; uncertainty has a bounded accumulated penalty.
- `SD-07`: recommend and ask on turns 1 through 9 when a useful unknown, inferred, or unresolved attribute exists; choose the highest relative average-impact question; recommend only with `ask_attribute = null` on turn 10.
- `SD-08`: ignore aggregate profile information in the baseline; any future use requires a named failure slice, paired ablation, controlled preference tags first, and no conflict or unrelated-category regression.
- `SD-09`: run one fixed quality pipeline with no runtime strategy trials; retain stage diagnostics for offline improvement; report technical failures and rerun rather than attempting partial-output recovery.
- `SD-10`: perform minimal response assembly with no natural-language generation or explanations; preserve ordered IDs and structured `ask_attribute`; use a contract-valid string placeholder.
- `SD-11`: use change-specific layered evaluation, grouped tuning and protected holdout sessions, predeclared experiment plans, complete reproducibility records, small-slice case inspection, and a full experiment ledger.

## Conceptual information flow to validate

### Offline catalog preparation

1. Preserve raw catalog records and product identity.
2. Produce traceable normalized facets, fielded lexical documents, and one dense embedding per product.
3. Build the searchable representations required by the three baseline retrieval routes.

### Session reset

1. Clear prior conversation-specific state for the session identifier.
2. Initialize empty raw history and active intent.
3. Receive but do not use the aggregate profile in baseline decisions.

### Per-turn flow

1. Link the incoming reply to the previous turn's structured `ask_attribute`, when present, and append both the raw message and structured turn context to session history.
2. Extract grounded turn claims and deterministic update operations.
3. Update current active intent while preserving unrelated claims and removing retracted or superseded preferences.
4. Create a fresh per-turn search state from current intent.
5. Construct one route-appropriate unified query for lexical, facet, and dense retrieval.
6. Retrieve equal-depth candidate lists from every route.
7. Deduplicate, preserve route evidence, apply RRF, and truncate to the experimental candidate budget.
8. Compare each candidate with active hard constraints and classify it as confirmed, provisional, or ineligible.
9. Rank confirmed and provisional candidates using the selected lexicographic groups, within-group scoring, and bounded uncertainty penalties.
10. Evaluate eligible question attributes through catalog coverage, candidate disagreement, and average branch impact, prioritizing expected top-ten changes.
11. Select recommendations and, on turns 1 through 9, the highest-value useful question; use `null` on turn 10 or when no useful question exists.
12. If no confirmed or provisional candidates remain, assemble the selected no-suitable-match response without relaxing requirements; otherwise assemble the minimal recommendation response without product claims or explanation.
13. Automatically validate the final response contract at the emission boundary.
14. Record per-stage diagnostics and any technical or final-validation failure for offline analysis and rerun.

### Next-turn feedback

If no terminating hit occurs, the simulator replies according to `ask_attribute` and scenario policy. The next message enters the same flow, while conversational history and current active intent carry across turns and all derived search state is rebuilt.

### Offline learning loop

Named failure evidence leads to a predeclared, paired experiment. A validated change may replace part of the next fixed baseline after capability evidence, regression checks, operational checks, and holdout validation. The active session never experiments on the user.

## State and evidence boundaries to validate

| Information | Lifetime | Authority |
|---|---|---|
| Raw catalog fields | Static | Product factual source |
| Derived catalog representations | Static until catalog rebuild | Search and normalization aids with provenance |
| Raw message history | One session | Conversational evidence and replay source |
| Structured question-reply context | One session | Links emitted `ask_attribute` to the next reply and records answered attributes |
| Current active intent | One session, mutable per turn | Current user meaning |
| Aggregate profile | One session input, unused baseline | Historical evidence only |
| Derived search state | One turn | Queries, candidates, assessments, ranking, and dialogue evidence |
| Diagnostic experiment record | Offline | Design-learning evidence, not runtime intent |

## Remaining experimental parameters

- facet schema, aliases, unit conversions, and compatibility rules;
- lexical field weights and dense representation choice;
- per-route retrieval depth, RRF settings, and fused candidate cutoff;
- normalization methods, within-group ranking weights, uncertainty increments, and penalty cap;
- question-impact feature combination and branch construction;
- tuning/holdout sizes and operational budgets;
- thresholds that trigger deferred multi-view retrieval, complex reranking, or personalization experiments.

These are explicit evidence-dependent parameters, not permission to silently change the selected conceptual behavior.

## Worked example or thought experiment

User message: "I need a backpack under $80. No leather, and it must fit a 15-inch laptop."

Trace the message through claim extraction, active-intent update, three retrieval routes, RRF truncation, constraint classification, ranking, question selection, and response assembly. At every boundary, identify the evidence that prevents a leather product, an unknown-material product, or a 13-inch product from being incorrectly treated as a confirmed fit.

## Learning experiment

Perform a paper trace for one Buying, Browsing, Intent Override, Boundary, and technical-failure session. For each stage record its conceptual input, output, preserved invariants, possible failure, and diagnostic evidence. The trace should expose any missing information or contradictory decision before implementation planning begins.

## My synthesis

### User's first integration validation

1. The user confirmed that the conceptual capability order correctly represents the selected system.
2. For the backpack example:
   - A is confirmed because reliable evidence satisfies the hard material, laptop-size, and budget constraints.
   - C is provisional because its material is missing while the other hard constraints match.
   - B is ineligible because leather contradicts the hard exclusion.
   - D is ineligible because 13-inch capacity contradicts the hard 15-inch requirement.
3. The agent must not ask about material again because the user's material requirement is already known. Other eligible attributes may be used to improve discrimination among candidates.

### Facilitator refinement

- Product C's material is product-side unknown evidence, not unresolved user intent. `SD-05` owns that assessment and keeps C provisional.
- Asking about another user attribute may improve retrieval or ranking, but it cannot establish that C is nylon. Only reliable catalog evidence or a corrected catalog representation could change that material assessment to confirmed.
- `SD-07` asks only about unresolved user-side information with actionable catalog coverage. It does not ask the user to repair missing product metadata.

The basic forward flow and the user-versus-product uncertainty boundary are validated.

### Learning-project failure boundary

The user explicitly rejected further optimization for rare runtime failures. If intent extraction or another capability errors, report the failure with its diagnostics and rerun the experiment after investigation. Do not reuse partial outputs, switch strategies, or design production-style recovery paths for this play project. A repeated unchanged top ten is likewise reported for offline analysis; it does not trigger runtime action.

Intent Override remains ordinary successful behavior rather than an error: the active intent replaces the leather preference with the leather exclusion and nylon requirement, unrelated requirements remain active, raw history preserves the original message, and all derived search state is rebuilt as already selected in `SD-03`.

## Connections to implementation planning

- Implementation remains optional until the user explicitly changes the phase.
- If implementation is chosen, unresolved experimental parameters need approved experiments or bounded baseline values.
- Conceptual capability boundaries must be translated into accepted implementation ADRs and small approved tasks without adding new system-design choices.

## Architecture critic feedback

Completed on `2026-09-17`. The critic found the system coherent as a learning baseline and identified these open findings before any implementation ADRs are drafted.

### Blocking clarifications

1. **Question and reply continuity:** raw user-message history alone cannot interpret a bare simulator reply such as `nylon` or prove that an attribute was already asked. The conceptual session state must preserve the prior structured `ask_attribute` and link it to the next reply.
2. **Unresolved interpretation disposition:** an unresolved update must be classified as resolvable through an allowed attribute question, intentionally ignored while prior intent remains active, or a failed run surfaced for investigation. Merely storing it leaves no defined consumer.
3. **Meaning of provisional recommendation:** `SD-05` through `SD-07` permit products with unknown hard-constraint evidence to be recommended and even outrank confirmed products, while `SD-10` emits no uncertainty disclosure. The user must define whether recommendation means "plausible candidate" or "known to satisfy the request" for this transferable design.
4. **Final contract-validity responsibility:** the integrated flow lists response invariants but does not assign conceptual responsibility for checking valid unique catalog identifiers, preserved order, allowed `ask_attribute`, required fields, and final-turn `null` immediately before emission.

### Non-blocking corrections or revisit items

- Remove stale `SD-09` connection language about fallback actions, retries, and cooldown state because the selected learning baseline only reports failures and reruns.
- Carry the selected no-candidate action from `SD-07` into the integrated flow.
- Place the bounded uncertainty penalty explicitly relative to the lexicographic ranking groups.
- Bound current-request relevance so it does not duplicate soft-preference, uncertainty, or retrieval-route evidence.
- Identify who constructs simulator-permitted answer branches for question-value comparison.
- Connect turn-level diagnostic records across turns for the three-turn stagnation report.

### Complexity observations

The critic suggested separating baseline behavior from study backlog because the always-on hybrid routes, RRF truncation, multi-part ranking policy, branch-simulated question value, deferred inferred views, personalization hooks, and unused response-grounding inputs create more degrees of freedom than the 200 public sessions may support reliably.

### Highest-value validation work

1. Paper-trace question and reply continuity for a bare value, no preference, override, and unresolved update.
2. Define the assertion made by confirmed-only, mixed confirmed/provisional, and provisional-only recommendation lists.
3. Trace normal, provisional-only, no-candidate, final-turn, unresolved-intent, and technical-failure terminal paths against the public contract.
4. Validate normalization-driven exclusions, RRF target loss, ranking sensitivity, and question-value proxies through separate fixed-input experiments.

These findings are critique evidence, not accepted design changes. The user decides which findings to resolve, defer, or reject.

### User resolutions to blocking findings

Accepted on `2026-09-17`:

1. Preserve each structured `ask_attribute` and link it to the next simulator reply in session history.
2. Clarify an unresolved user interpretation through an allowed attribute only when its question value is high enough to be selected by `SD-07`; otherwise ignore the update, preserve prior active intent, and retain the evidence for investigation.
3. Define a provisional recommendation as a plausible non-contradictory candidate, not an assertion that every hard requirement is confirmed.
4. Automatically assign final contract validation to the response-emission boundary. Validation failure is reported and the learning run is rerun.

These resolutions close the critic's blocking clarifications. Non-blocking simplifications and experimental risks remain revisit items rather than barriers to the conceptual design.

## Revisit conditions

Revisit any source SDR when the integrated paper traces reveal missing evidence, conflicting capability assumptions, an invariant that cannot cross a boundary, or an experimental parameter that actually changes conceptual behavior.
