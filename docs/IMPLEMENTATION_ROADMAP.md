# Implementation Roadmap

- Status: `Approved`
- Date: `2026-09-17`
- Approved by user: `2026-09-17`
- Source architecture: `SDR-001` through `SDR-012`
- Current phase: `IMPLEMENTING`

## Purpose

Translate the synthesized conceptual agent into small, evidence-backed implementation milestones. Each milestone is prepared just in time: accept only the implementation ADRs it actually needs, approve one observable task at a time, verify each task, then run the milestone experiment before continuing.

This roadmap orders work. A later user instruction to implement a named milestone authorizes Codex to make the bounded implementation decisions, prepare the small tasks, and write the code needed for that milestone. It does not authorize a conceptual redesign or the adoption of an experimental alternative.

## Implementation ownership and learning boundary

- The user owns the system-design intent and every experiment-based keep, change, remove, or defer decision.
- After the user asks to implement a named milestone, Codex owns local implementation decisions inside that milestone and the accepted system design. Codex records consequential choices and their reasoning without asking the user to select routine coding details.
- The milestone authorization is the user's approval for its bounded implementation tasks. Each task must still satisfy the repository's small-task standard and be recorded as `Approved under Mx authorization` before code is written.
- Codex may run deterministic tests, contract checks, and inspections needed to establish that the implementation works as specified.
- Codex must not run the milestone's comparison experiment on the user's behalf. It stops at the experiment checkpoint and hands over a small, reproducible procedure, fixed inputs, measurements, examples to inspect, and the decision to be made.
- After the user reports the experiment result and chooses an alternative, Codex may revise the affected implementation under that decision.
- If implementation exposes a conceptual gap or requires work outside the named milestone, Codex stops and returns the issue to the user.
- Simplicity is a design constraint: implement the shortest clear version that teaches the current capability. Production hardening, broad edge-case handling, and speculative abstractions remain out of scope unless required by the official contract, fixed data, or observed experiment evidence.

## Operating loop for every milestone

1. The user asks Codex to implement the named milestone.
2. Confirm the milestone outcome, dependencies, non-goals, and experiment gate.
3. Inspect only the source and data needed for that milestone.
4. Autonomously choose the simplest implementation details consistent with accepted decisions; record an ADR only when the choice has consequences across tasks.
5. Prepare and execute one small approved-under-milestone task at a time.
6. Implement, review, and verify each task before drafting the next task.
7. Summarize the completed code in learner-readable terms and hand the fixed-input experiment to the user.
8. Stop for the user's experimental evaluation and keep/change/defer decision.
9. Apply the user's decision and record the milestone result.
10. After the milestone is complete, commit all current repository changes and push the current branch.
11. Move to the next milestone only when the user requests it.

No milestone is complete merely because its code exists. Its exit evidence must be recorded.

Expected task categories below are a menu of work that may become necessary, not permission to implement every listed mechanism. The smallest behavior needed to reach the experiment checkpoint wins.

## Phase map and rough effort

| Learning implementation phase | Roadmap milestone | Manual experiment checkpoint | Focused implementation time |
| --- | --- | --- | --- |
| Foundation | M0 | Deterministic readiness evidence only | Complete |
| Catalog representations | M1 | Compare raw records with derived claims on a small fixed sample | 1-2 days |
| Intent and session state | M2 | Replay fixed messages and inspect active intent after each turn | 1-2 days |
| Retrieval baselines | M3 | Compare lexical, facet, dense, and combined target coverage on identical sessions | 2-3 days |
| Fusion and eligibility | M4 | Compare union/RRF and candidate cutoffs; inspect false exclusions | 1-2 days |
| Ranking | M5 | Compare simple ranking variants on identical fixed candidate pools | 1-2 days |
| Dialogue policy | M6 | Check whether selected questions can change the top-ten result | 1 day |
| End-to-end agent | M7 | Run the public evaluator and inspect scenario slices and attributed misses | 1-2 days |
| Controlled refinement | M8 | Run protected validation, then choose whether one failure slice warrants another iteration | 1-2 days per iteration |

The baseline is expected to take roughly 8-13 focused implementation days plus 6-10 hours of user-run experiments. Additional retrieval or refinement work is added only after an experiment justifies it.

## Baseline scope carried from system design

- Raw catalog fields remain factual truth.
- Baseline catalog views are normalized facets, a fielded lexical representation, and one dense representation.
- Intent extraction is deterministic for the simulator grammar; observed claims remain separate from inference.
- Session state retains raw turn history, structured question-reply links, and current active intent; search state is rebuilt every turn.
- Baseline retrieval uses lexical, facet, and dense routes, followed by RRF and a bounded candidate pool.
- Only reliable contradictions exclude; unknown or inferred hard-constraint evidence remains provisional.
- Ranking uses the selected lexicographic signal groups with separately normalized within-group scores.
- Dialogue recommends and asks when a useful question exists on turns 1 through 9; turn 10 uses `ask_attribute = null`.
- Aggregate profile information is ignored in the baseline.
- Runtime quality strategy is fixed; failed experimental runs are reported and rerun rather than recovered dynamically.
- Response text is a minimal placeholder; the structured response is validated automatically before emission.

## Deferred backlog, not baseline work

- LLM-generated catalog or conversational representations;
- multi-view dense retrieval;
- learned sparse or token-level multi-vector retrieval;
- taxonomy or graph retrieval;
- learned or semantic reranking;
- personalization;
- runtime quality switching;
- natural-language recommendation explanations.

Add one only after its recorded failure trigger and experiment justify reopening the responsible SDR.

## M0 — Implementation readiness and evidence inventory

### Outcome

The repository, frozen data, starter boundary, evaluator entry points, runtime assumptions, and existing baseline evidence are understood well enough to write the first implementation ADR and task without guessing.

### Dependencies

- Synthesized `SDR-001` through `SDR-012`.
- Official contract documents and project standards.

### Likely documents

- A readiness report or recorded inspection evidence.
- ADRs only if the inspection exposes an immediate implementation choice.
- The first approved task for M1.

### Expected work categories

- Verify catalog and evaluator availability without modifying official artifacts.
- Inspect the starter boundary and existing dependency/runtime configuration.
- Record current tests, commands, data paths, and blockers.
- Confirm which conceptual parameters require experiments rather than early hard-coding.

### Experiment or evidence gate

No performance experiment is required. Produce deterministic evidence that required inputs exist, identify missing prerequisites, and record exact commands that can be reproduced.

### Complete when

- Required data and boundaries are located or precisely recorded as missing.
- No contract conflict is unresolved.
- The first implementation ADRs and one M1 task can be drafted without inventing system-design decisions.

## M1 — Catalog truth, identity, normalization, and provenance

- Status: `Complete — 2026-09-21`

### Outcome

Catalog products can be loaded by `parent_asin`, raw fields remain unchanged, and selected normalized facets retain source evidence and provenance for later constraint decisions.

### Dependencies

- M0 readiness evidence.
- `SDR-001` and normalization decisions in `SDR-005`.

### Likely ADR topics

- Internal product and claim representation.
- Normalized-facet schema and provenance representation.
- Catalog/index persistence only if more than one viable choice materially affects later work.

### Expected task categories

- Catalog loading and identity validation.
- Raw-field preservation.
- One numeric price claim that abstains for missing or unsupported values.
- One normalized category claim that preserves order and removes repeated values.
- Source-field links for both derived claim types.

Aliases, unit conversion, component scope, compatibility, nested-detail facets, and conflict handling are deferred until a later capability or observed experiment failure requires them.

### Experiment gate

Inspect fixed numeric, null, string-price, and repeated-category records. Decide whether string prices remain unsupported, repeated categories are deduplicated, and price/category use separate or shared claim types.

### Complete when

- Focused tests prove raw records remain unchanged and derived claims retain source-field links.
- Fixed-catalog claim counts are recorded.
- The user records the three representation decisions from the experiment.
- Any unimplemented normalization behavior is explicitly deferred rather than treated as supported evidence.

### Completion evidence

- `TASK-001`, `TASK-002`, and `TASK-003` are verified.
- The repository suite passes 18 tests.
- The fixed catalog emits 10,410 numeric price claims and 238,277 normalized category claims.
- On `2026-09-21`, the user chose to keep string prices unsupported, deduplicate repeated categories, and retain separate claim types.

## M2 — Deterministic intent and conversational state

- Status: `Complete — 2026-09-22`

### Outcome

Simulator messages become grounded claims; raw turn history, structured `ask_attribute` links, and current active intent evolve correctly across additions, indifference, replacement, override, and reset.

### Dependencies

- M1 catalog vocabulary where normalization requires it.
- `SDR-002`, `SDR-003`, and the critic resolutions in `SDR-012`.

### Likely ADR topics

- Claim and stance representation.
- Current-intent representation and deterministic update operations.
- Structured turn record and question-reply linkage.

### Expected task categories

- Observed claim extraction for one bounded template family at a time.
- Negation, strength, and indifference handling.
- Add, replace, cancel, and override behavior.
- Reset isolation.
- Bare-value reply interpretation through prior `ask_attribute`.
- Unresolved-update behavior and diagnostic reporting.

### Experiment gate

Paper and automated traces for a bare-value reply, no-preference reply, override, unresolved update, and reset. Evaluate complete claim frames rather than only individual tokens.

### Complete when

- The fixed simulator-template suite passes.
- Current intent contains no superseded influence.
- Question-reply continuity and reset isolation have evidence.

### Completion evidence

- `TASK-004`, `TASK-005`, and experiment-driven correction `TASK-006` are verified.
- The repository suite passes 32 tests.
- Known simulator templates produce observed claims; unknown unlinked messages remain unresolved without changing active intent.
- Active intent contains at most one claim per attribute.
- Indifference and override replace only their matching attribute.
- Raw turn history, question-reply linkage, unresolved-turn history, and reset isolation have focused test evidence.
- On `2026-09-22`, the user retained preferred attribute replies and selected the final indifference, override, and unresolved-turn behavior.

## M3 — Baseline catalog representations and retrieval routes

### Outcome

Fielded lexical, facet, and single-vector dense routes can each retrieve equal-depth candidate lists with route evidence from a unified current-intent query.

### Dependencies

- M1 catalog truth and representations.
- M2 current intent.
- `SDR-004`.

### Likely ADR topics

- Lexical retrieval/index choice and field weighting.
- Dense embedding model and index/search choice.
- Facet-route ordering inputs.
- Query representation shared boundaries.

### Expected task categories

- Fielded lexical representation and BM25-style retrieval.
- Facet retrieval and matched-facet evidence.
- Single-vector dense representation and retrieval.
- Route-local ranks, scores, and deterministic candidate identity.
- Equal-depth route execution.

### Experiment gate

Compare route Recall@K, unique target contribution, overlap, latency, and failure slices on identical tuning sessions. Do not use final reranking to judge route coverage.

### Complete when

- Every route has focused correctness tests.
- Route-level comparison evidence exists.
- Deferred retrieval families remain deferred or have a named evidence-backed trigger.

## M4 — Candidate fusion and constraint-aware selection

### Outcome

Route outputs are deduplicated and fused through RRF, the candidate budget is applied, and retained candidates are classified as confirmed, provisional, or ineligible without treating missing evidence as contradiction.

### Dependencies

- M3 retrieval routes.
- M1 evidence and M2 hard constraints.
- `SDR-004` and `SDR-005`.

### Likely ADR topics

- Candidate-evidence representation across routes.
- RRF and candidate-budget parameter ownership.
- Typed constraint-comparison boundary.

### Expected task categories

- Candidate union, deduplication, and route provenance.
- Deterministic RRF.
- Configurable post-fusion cutoff.
- Categorical, numeric, range, exclusion, component, and compatibility comparison.
- Confirmed/provisional/ineligible aggregation and exclusion reasons.

### Experiment gate

Compare route-level target presence, full union, post-RRF order, and several cutoffs. Separately measure false exclusion, contradiction leakage, and retained candidate count on fixed candidates.

### Complete when

- The selected cutoff has recorded evidence rather than being inferred from final top ten.
- Confirmed contradictions never survive.
- Unknown and inferred evidence remain provisional.
- Every exclusion is traceable.

## M5 — Ranking baseline

### Outcome

Confirmed and provisional candidates receive deterministic final ordering from direct current relevance, retrieval evidence, soft preferences, and popularity tie-breaking without signal duplication.

### Dependencies

- M4 retained candidates and evidence.
- `SDR-006` and the non-blocking critic findings in `SDR-012`.

### Likely ADR topics

- Exact definition of each ranking feature group.
- Placement and cap of uncertainty penalties.
- Per-signal normalization and parameter-selection process.

### Expected task categories

- Direct relevance features independent from route evidence.
- Retrieval-evidence features.
- Soft-preference features.
- Accumulated bounded uncertainty penalty.
- Exact lexicographic group comparison.
- Deterministic popularity tie-breaking.

### Experiment gate

Use fixed retained candidate sets to select weights and penalty values, measure MRR and HitRate@10, inspect target movement, and perturb near-equal higher-priority scores to test stability.

### Complete when

- Feature ownership prevents double counting.
- Parameter choices have tuning evidence.
- Exact hierarchy is retained or reopened according to its recorded sensitivity trigger.

## M6 — Dialogue policy and minimal contract response

### Outcome

The agent selects a useful allowed `ask_attribute`, recommends on every valid turn, applies the final-turn rule, handles no-candidate output, and emits an automatically validated minimal response.

### Dependencies

- M2 question-reply context.
- M4 eligibility and M5 ranking.
- `SDR-007`, `SDR-010`, and critic resolutions in `SDR-012`.

### Likely ADR topics

- Construction of simulator-permitted answer branches.
- Exact within-turn question-impact representation.
- Final response-validation responsibility and failure reporting.

### Expected task categories

- Eligible-attribute gates and repeat prevention.
- Catalog coverage and candidate-disagreement evidence.
- Average branch-impact comparison prioritizing top-ten change.
- Recommend-and-ask behavior for turns 1 through 9.
- Final-turn `null` and no-useful-question `null`.
- Provisional-only and no-candidate responses.
- Minimal message, ordered IDs, optional usage, and final contract validation.

### Experiment gate

Trace fixed dialogue states and simulator-permitted replies through eligibility and ranking. Compare selected questions with recommend-only, and cover normal, provisional-only, no-candidate, unresolved-intent, final-turn, and validation-failure paths.

### Complete when

- Selected questions have measurable downstream effect on the fixed examples.
- Answered attributes are not repeated.
- Every terminal path is defined and contract-valid except explicitly reported failed experimental runs.

## M7 — Fixed end-to-end agent and diagnostics

### Outcome

The accepted capabilities execute as one fixed per-turn pipeline with rebuilt search state and enough stage evidence to attribute misses offline.

### Dependencies

- M1 through M6.
- `SDR-009`, `SDR-011`, and `SDR-012`.

### Likely ADR topics

- Per-stage diagnostic record and experiment artifact format.
- Only coordination choices that are not already fixed by the conceptual flow.

### Expected task categories

- Reset-to-turn integration.
- Stage diagnostics and cross-turn stagnation reporting.
- Failure reporting and rerun evidence.
- Reproducible evaluator command and experiment manifest.

### Experiment gate

Run the grouped tuning sessions end to end. Report official metrics, scenario slices, per-stage target-loss attribution, latency, memory, exceptions, and repeatability. Do not inspect the protected holdout during ordinary tuning.

### Complete when

- End-to-end behavior matches accepted decisions.
- Misses can be attributed where evidence permits.
- Operational evidence is recorded.
- No invariant or guardrail failure remains unresolved.

## M8 — Protected milestone validation and baseline decision

### Outcome

The completed fixed baseline receives sparse milestone validation and the study records what was learned without automatically expanding scope.

### Dependencies

- M7 tuning evidence and all experiment records.
- `SDR-011` holdout discipline.

### Likely ADR topics

None unless validation exposes a conceptual gap. New feature ideas return to the relevant SDR rather than being added inside M8.

### Expected task categories

- Freeze the candidate configuration and experiment manifest.
- Run the protected holdout once for the approved milestone question.
- Record raw counts, scenario slices, limitations, and holdout access.
- Accept the baseline, adjust an experimental parameter on tuning data, or return a design issue to ARCHITECTING.

### Experiment gate

The holdout run is the gate. Synthetic or LLM-generated sessions, if later approved, are supplemental and reported separately.

### Complete when

- Holdout evidence and access are recorded.
- Rejected and inconclusive variants remain in the experiment ledger.
- The user explicitly decides whether the learning implementation is complete or another named failure slice warrants a new cycle.

## Roadmap approval and phase gate

Before moving `Phase` to `IMPLEMENTING`:

- the user approves this roadmap;
- M0 is selected as active;
- any ADR required before the first mutation is accepted;
- one M0 or M1 task satisfies the small-task standard and is marked `Approved` by the user.

Only the user may approve the roadmap, waive evidence, authorize a project phase change, or choose an experimental alternative. A direct instruction to implement a named roadmap milestone is explicit authorization for Codex to make and record bounded implementation decisions and to approve its small tasks under that milestone authorization. It is not authorization to cross the experiment checkpoint.
