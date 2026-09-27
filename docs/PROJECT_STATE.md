# Project State

This file is the phase gate for Codex and the shared progress index.

- Phase: `VERIFYING`
- Current learning card: `None` (LC-00 through LC-14 complete)
- Architecture status: `SYNTHESIZED` — architecture critique complete; blocking clarifications resolved
- Active system-design area: `SD-12` — Synthesized; critique resolutions recorded
- Active design record: `SDR-012` — Synthesized
- Active implementation ADRs: `ADR-007`, `ADR-009` — Accepted under M3 authorization
- Active implementation task: `None` — M3 complete
- Last verified implementation task: `TASK-018`
- Implementation roadmap: `Approved` by the user on `2026-09-17`
- Active implementation milestone: `M3` — Complete
- Next planning item: `Await user instruction before preparing M4 fusion and eligibility work`
- Latest project update: `M3 completed with provisional BM25/facet/SVD-256 routes, first-turn holdout deferred until dialogue integration, and the complete repository suite passing 70/70 tests; changes are ready to publish (2026-09-27)`

## Learning progress

- LC-00: `Complete` at the user's request. Conceptual teach-back recorded; numerical exercise skipped at the user's request, not verified.
- LC-01: `Complete` at the user's request. Teach-back and follow-up on unsupported product claims recorded, with tutor clarifications.
- LC-02: `Complete` at the user's request. Teach-back and tutor refinements recorded; the optional preferred-versus-required follow-up was not answered and carries into LC-03.
- LC-03: `Complete` at the user's request. Teach-back recorded for preference strength, negation scope, and replacement/addition; tutor clarified the change from soft leather preference to hard nylon requirement.
- LC-04: `Complete` at the user's request. Teach-back recorded for lexical mismatch, soft-preference handling, and diagnosing coverage gains with top-ten ranking losses.
- LC-05: `Complete` at the user's request. Teach-back recorded for unknown versus mismatch, justified exclusion, and the effect of false exclusion on downstream ranking.
- LC-06: `Complete` at the user's request. Teach-back recorded for incomparable score scales, fixed-candidate ranking experiments, and hard-constraint priority.
- LC-07: `Complete` at the user's request. Teach-back recorded for explicit versus inferred evidence, superseding preferences, and session reset isolation.
- LC-08: `Complete` at the user's request. Teach-back recorded for question value, actionable answers, and asking while recommending; tutor clarified turn cost and evidence availability.
- LC-09: `Complete` at the user's request. Teach-back recorded for preserving unrelated requirements, indifference versus unknown, and hidden stale-state effects.
- LC-10: `Complete` at the user's request. Teach-back recorded for historical priors, relevant tie-breaking, and over-personalization causing target exclusion.
- LC-11: `Complete` at the user's request. Teach-back recorded for failure proxies, fallback triggers versus bounded fallback definitions, and cooldown behavior.
- LC-12: `Complete` at the user's request. Teach-back recorded for leakage versus overfitting, paired ablations, and aggregate results hiding scenario regressions.
- LC-13: `Complete` at the user's request. Teach-back recorded for timeout risk, usage reporting, and missing operational evidence; tutor supplied the remaining comparison dimensions.
- LC-14: `Complete` at the user's request. Teach-back recorded for intent corruption at message understanding, preserving hard requirements end to end, and tracing a retrieved target lost during reranking.

## Allowed phase values

`LEARNING` -> `ARCHITECTING` -> `IMPLEMENTING` -> `VERIFYING`

A phase changes only after the user explicitly approves it and this file is updated. Moving backward is allowed when implementation exposes a missing decision.

## Transition checks

### LEARNING to ARCHITECTING

- The relevant learning cards contain the user's own conclusions.
- Major unknowns are listed rather than silently assumed.
- The user explicitly says they are ready to propose an architecture.

### ARCHITECTING to IMPLEMENTING

- The user explicitly chooses to implement rather than continue system-design study only.
- The user-authored conceptual agent covers the capabilities relevant to that implementation goal.
- Relevant conceptual choices are translated into accepted implementation ADRs.
- Risks have validation plans, and the first task is small, complete, and marked `Approved` by the user.

### IMPLEMENTING to VERIFYING

- The implementer has supplied criterion-by-criterion evidence.
- Focused tests pass or failures are explicitly recorded.
- The implementation is ready for independent review.

### VERIFYING to next task

- No unresolved high-priority finding remains.
- Every acceptance criterion is PASS or explicitly waived by the user.
- The completed task and next active item are recorded here.
