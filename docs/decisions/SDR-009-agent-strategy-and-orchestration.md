# SDR-009: Agent strategy and orchestration

- Status: `Synthesized`
- Author: `User`
- Date: `2026-09-17`
- System-design area: `SD-09`
- Related learning cards: `LC-11`, `LC-13`, `LC-14`
- Case-study references: `docs/competition_specification.md`, `docs/agent_api_contract.json`, `docs/evaluation_config.json`, `docs/submission_rules.md`

## System question

How should the agent coordinate the selected capabilities, detect that its current behavior is failing without seeing the hidden target, and invoke bounded recovery strategies without oscillation, silent requirement relaxation, or operational failure?

## Why this capability matters

The baseline capabilities can each behave correctly yet still produce a poor end-to-end result. Retrieval may stagnate, fusion may remove a uniquely retrieved target, constraint processing may leave only uncertain products, ranking may remain unchanged, or questions may have no effect. Orchestration observes these conditions, selects from explicitly permitted strategies, and ensures that state and invariants remain coherent across turns.

## Information available

- current turn and remaining turn budget;
- whether the previous recommendations produced a terminating hit, inferred indirectly because the session either ended or continued;
- current active intent and whether it changed materially;
- retrieval route candidates, unique contribution, overlap, fused-pool composition, and cutoff effects;
- confirmed, provisional, and ineligible candidate counts plus exclusion reasons;
- ranking order, score evidence, margins, and movement from earlier turns;
- asked attribute, reply effect, and whether candidate eligibility or ranking changed;
- latency, timeout proximity, exceptions, dependency availability, and model-usage information;
- current strategy, prior switches, retry count, and reason for each switch.

The hidden target, private intent card, exact scenario label, and future simulator behavior remain unavailable.

## Useful representations

A turn-level health and strategy view may include:

- intent-change status;
- candidate counts at retrieval, fusion, constraint, ranking, and final-output stages;
- overlap with the previous turn's candidate and top-ten sets;
- uncertainty, missingness, and contradiction summaries;
- question effect on intent, eligibility, and rank;
- operational health and remaining budget;
- active strategy and fallback mode;
- trigger evidence, permitted action, retry count, cooldown, stopping condition, and observed result.

This view is derived operational state, not conversational truth. It is rebuilt or updated from observable capability outputs and must reset with the session.

## Solution families to learn

- one fixed end-to-end pipeline with no runtime switching;
- rule-based fallbacks triggered by explicit observable conditions;
- decision tables or finite-state strategy controllers;
- confidence- or health-score routing;
- planner or LLM-directed tool and strategy selection;
- contextual bandits or reinforcement learning over multi-turn outcomes;
- cascaded quality-versus-cost strategies;
- degraded modes for unavailable models, network failures, or latency pressure.

## What I need to research

- Concepts and vocabulary: orchestration, routing, policy, trigger, fallback, retry, cooldown, hysteresis, circuit breaker, degraded mode, invariant, health signal, stagnation, oscillation, and finite-horizon control.
- Algorithms or system patterns: decision tables, finite-state controllers, confidence routing, bounded retries, circuit breakers, multi-armed bandits, contextual bandits, and cascaded inference.
- Questions the research must answer:
  - Which observable signals distinguish retrieval, fusion, constraint, ranking, dialogue, and operational failures?
  - Which recovery action is permitted for each failure class?
  - Which invariants must every fallback preserve?
  - How many retries or switches are useful within ten turns?
  - What cooldown evidence prevents oscillation without delaying necessary recovery?
  - When should the agent stop adapting and return the safest valid response?
  - What failure evidence would justify moving beyond deterministic orchestration?

## Comparison criteria

- recovery of sessions missed by the fixed baseline;
- false-trigger rate and unnecessary strategy switches;
- repeated-list, repeated-question, and no-effect-turn rates;
- preservation of hard requirements and current intent;
- target survival and rank movement by capability stage;
- switch count, oscillation, and recovery latency;
- timeout, exception, and invalid-output rates;
- determinism, traceability, token cost, latency, and memory;
- behavior by scenario and remaining-turn slice.

## Worked example or thought experiment

Turn 1 returns a top ten from the baseline pipeline and asks about laptop size. The session continues. On turn 2 the reply adds a 15-inch requirement, but the same top ten and nearly identical order reappear. Constraint evidence shows that several listed products have unknown laptop compatibility, and the dense route found unique candidates that RRF truncation removed.

Possible diagnoses include stale intent propagation, fusion-induced candidate loss, missing compatibility evidence, or a ranking policy that underweights the new requirement. An orchestrator should not switch strategies until the observable evidence identifies which capability's recovery is appropriate.

## Learning experiment

Replay fixed multi-turn sessions through the baseline and an explicit fallback decision table. For every trigger, record:

- the observed evidence;
- the diagnosed failure class;
- the permitted strategy change;
- preserved invariants;
- retry and cooldown rules;
- candidate and rank changes;
- whether the session recovered or merely changed behavior.

Compare baseline versus orchestration on core metrics, recovered misses, false triggers, strategy switches, oscillation, latency, and scenario slices. Introduce a learned controller only if repeated decision patterns cannot be captured by stable observable rules.

## My synthesis

### User's initial direction

1. Use one fixed runtime pipeline with no quality-driven strategy switching.
2. Capture failures and diagnostic evidence for offline analysis and improvement rather than trying alternative retrieval, fusion, constraint, ranking, or dialogue strategies during the active session.
3. Treat three consecutive continued turns with unchanged intent and the same or nearly identical top ten as a stagnation signal for offline investigation.
4. Do not automatically try a fixed fallback sequence or a stage-specific quality recovery at runtime.
5. For this learning project, do not recover from a technical capability failure by reusing partial output or switching strategy. Report the failing capability and available diagnostics, treat the run as invalid, and rerun after investigation.
6. Surface every technical failure for manual investigation with the failing capability, failure category, and available stage evidence.
7. Retain offline diagnostic evidence including per-stage candidate identities and counts, exclusion reasons, ranking contributions, question effects, latency, and the final top ten.
8. Promote an offline improvement into the fixed runtime baseline only after a paired ablation on the named failure slice, regression checks on other slices, and holdout validation.

### Facilitator refinement

- The three-turn stagnation signal is diagnostic only. It does not alter the current session's strategy, relax constraints, expand retrieval, or bypass RRF.
- Offline diagnosis should still use stage-specific evidence so a later design change addresses the responsible capability rather than introducing a global workaround.
- Intent Override can legitimately continue before the replacement intent arrives. Stagnation analysis must separate pre-override trajectories and meaningful intent changes from ordinary repeated failures.
- No quality-driven switching does not yet define behavior for technical failures such as exceptions, unavailable dependencies, or timeout risk. Contract-safe failure containment remains an operational question rather than an online quality experiment.
- The project is intended to teach and compare concepts rather than provide production availability. Reporting and rerunning a failed experiment is preferred to designing partial-output recovery paths that do not advance the learning objective.
- If the official evaluator is run, an exception or missing response may count as a miss. This trade-off is accepted for the learning scope rather than optimized through runtime recovery.

The initial orchestration policy is fully deterministic. Runtime quality adaptation, learned control, and automatic strategy trials remain deferred unless offline evidence later demonstrates a repeated need.

## Connections to the rest of the agent

- Information required from upstream capabilities: intent changes, per-stage candidates and evidence, ranking movement, dialogue effects, and operational health from `SD-01` through `SD-08`.
- Information supplied to downstream capabilities: the fixed selected strategy, preserved invariants, and diagnostic reason. No quality fallback, retry, or cooldown state is produced in the baseline.
- New questions created for later areas: how response grounding exposes degraded behavior, how evaluation attributes recovery to the correct capability, and how the final conceptual agent represents control flow.

## Architecture critic feedback

Awaiting user synthesis.

## Revisit conditions

Revisit when the fixed pipeline repeatedly fails without observable recovery, rule-based fallbacks trigger incorrectly, strategies oscillate, runtime budgets are exceeded, or evaluation exposes a decision pattern that deterministic controls cannot express.
