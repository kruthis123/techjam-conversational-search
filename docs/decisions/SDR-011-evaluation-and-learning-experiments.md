# SDR-011: Evaluation and learning experiments

- Status: `Synthesized`
- Author: `User`
- Date: `2026-09-17`
- System-design area: `SD-11`
- Related learning cards: `LC-00`, `LC-12`, `LC-13`
- Case-study references: `docs/competition_specification.md`, `docs/evaluation_config.json`, `docs/submission_rules.md`

## System question

How should capability alternatives and the complete agent be evaluated so improvements are attributable, generalize beyond repeatedly viewed development sessions, preserve safety invariants, and remain operationally feasible?

## Why this capability matters

The official metrics determine end-to-end success but do not identify the responsible capability. Aggregate gains can hide retrieval losses, false exclusions, scenario regressions, leakage, or excessive latency. Every design area has deferred parameter values or alternatives to experiments, so the system needs one coherent evidence process rather than ad hoc tuning against the same sessions.

## Information available

- the frozen 50,000-product catalog;
- 200 labelled public development sessions and 800 private organizer sessions;
- official global and scenario-sliced metrics;
- deterministic simulator trajectories and per-session outcomes when the local data is available;
- per-stage diagnostics selected in `SD-09`;
- capability-specific labels or expected outcomes created from simulator frames, catalog evidence, and manually checked contrast cases;
- latency, token usage, memory, dependency, exception, and timeout evidence collected locally.

Private targets, private intent cards, and private simulator state remain unavailable. Public target labels are evaluation evidence and must never enter runtime inputs.

## Useful representations

An experiment record may include:

- question or hypothesis and named failure slice;
- baseline and one changed factor;
- fixed data split, candidate sets, seeds, and configuration;
- capability metrics, end-to-end metrics, scenario slices, and operational measures;
- per-session target movement and error category;
- acceptance guardrails and revisit conditions;
- uncertainty or sample-size caveats;
- result, decision, and whether the holdout was consumed;
- artifacts needed to reproduce the comparison.

An error taxonomy should attribute misses to intent extraction, stale state, retrieval omission, fusion cutoff, false exclusion, ranking demotion, question policy, contract failure, or timeout where evidence permits.

## Solution families to learn

- end-to-end score-only comparison;
- layered evaluation with contract, capability, integration, scenario, and end-to-end evidence;
- paired ablations on identical sessions;
- fixed-candidate counterfactual tests for ranking and question policies;
- product- or intent-grouped development and holdout splits;
- cross-validation or repeated resampling when public data is limited;
- regression suites built from named failure cases;
- simulation replay and synthetic contrast sets;
- experiment tracking and reproducibility manifests;
- confidence intervals or uncertainty-aware comparison for small slices.

## What I need to research

- Concepts and vocabulary: baseline, ablation, paired comparison, holdout, leakage, overfitting, selection bias, counterfactual, error slice, regression, confidence interval, statistical power, and reproducibility.
- Algorithms or system patterns: grouped splitting, cross-validation, bootstrap comparison, staged evaluation, error attribution, and experiment tracking.
- Questions the research must answer:
  - Which evidence must pass before an end-to-end evaluator run is meaningful?
  - Which metric isolates each capability from upstream changes?
  - How should the 200 public sessions be divided between tuning and final checking?
  - How can product and template leakage be prevented?
  - Which regressions are unacceptable even when aggregate score improves?
  - How often may the holdout be inspected before it becomes another tuning set?
  - How should small scenario slices be interpreted without overclaiming?
  - Which operational measurements are required before calling a variant feasible?

## Comparison criteria

- official HitRate@10, MRR, MTTC, Efficiency, and TechnicalScore;
- Buying, Browsing, Intent Override, and Boundary slices;
- capability-specific quality and named failure slices;
- contract-valid response and exception rates;
- timeout, per-turn latency, peak memory, package size, dependency availability, token use, and cost;
- repeatability across seeds or runs where nondeterminism exists;
- false-exclusion, contradiction-leakage, unsupported-claim, and stale-state rates;
- evidence of generalization rather than repeated public-set adaptation.

## Worked example or thought experiment

A ranking-weight change raises aggregate MRR but lowers retrieval-independent ranking MRR on Intent Override sessions. Investigation shows that the experiment also changed candidate generation, so the target sets were not fixed. The aggregate result cannot establish that ranking improved.

A valid ranking comparison holds candidate sets constant, changes only the ranking policy, compares the same sessions, inspects target movement, and checks scenario slices. A later end-to-end run then measures whether the ranking improvement survives interaction with retrieval and dialogue.

## Learning experiment

Build a paper evaluation matrix before running models:

| Capability | Fixed input | Diagnostic output |
|---|---|---|
| Intent understanding | messages and expected claim frames | claim, stance, negation, and update accuracy |
| Retrieval | intent and catalog representations | Recall@K and unique route contribution |
| Constraint selection | fixed candidates and catalog evidence | target survival, false exclusion, contradiction leakage |
| Ranking | fixed retained candidates | MRR, HitRate@10, and target movement |
| Dialogue | fixed state and answer branches | useful-question rate and post-answer rank or eligibility change |
| Orchestration | fixed failures and stage outputs | valid containment, diagnostic attribution, and no unsafe bypass |
| End to end | complete sessions | official metrics and scenario slices |
| Operations | repeatable runs | latency, timeout, memory, dependencies, and usage reporting |

Use paired, one-factor comparisons and a protected holdout. Promote a change only when its named capability evidence improves, end-to-end behavior remains acceptable, guardrail slices do not regress, and operational evidence is sufficient.

## My synthesis

### User's initial direction

1. Do not require one universal sequence in which every change must pass a capability-specific evaluation before an end-to-end run. Select the appropriate evaluation layers according to the change being tested.
2. Divide the public sessions into a product- or intent-grouped tuning set and a protected holdout used for milestone decisions.
3. Decide experiment-specific adoption conditions as part of designing each experiment rather than fixing one universal set of numeric thresholds now.
4. Require a written experiment plan before execution containing the hypothesis, baseline, changed factor, data split, selected evaluation layers, metrics, slices, and adoption criteria.
5. Keep the holdout physically and procedurally separate from development data and inspect it only for sparse milestone decisions rather than routine tuning.
6. For small slices, report raw session counts and inspect individual failures in addition to reporting aggregate or percentage metrics.
7. Use one protected holdout rather than subdividing the limited 200 public sessions into an additional final lockbox. If more evaluation cases are needed later, consider separately generated synthetic sessions as supplemental evidence.
8. Retain, at minimum, the data-split identity, catalog and configuration version, random seed, exact run command, environment information, per-session results, and aggregate metrics for every experiment.
9. Keep rejected and inconclusive experiments in the same experiment history as successful variants.

### Facilitator refinement

- The evaluation route may depend on scope: an isolated ranker change benefits from fixed-candidate ranking evaluation, while an interaction change may require an end-to-end replay earlier. The experiment must state why its selected layers can establish the claimed effect.
- Experiment-specific metrics, thresholds, and acceptable trade-offs should be chosen before inspecting the comparison result. Choosing them after seeing results creates selection bias and makes rejection criteria movable.
- Earlier system-design invariants are not optional experiment thresholds. Contract validity, no recommendation of confirmed hard contradictions, session isolation, no baseline profile influence, and no final-turn question remain required regardless of aggregate TechnicalScore.
- If an unexpected result motivates a new metric or threshold, record it as a new hypothesis and test it on data not used to invent that criterion rather than retroactively declaring the original variant successful.
- Keeping holdout sessions in a separate file does not by itself preserve independence. If their results influence subsequent design choices, repeated adaptation can still overfit to them. Record each holdout access and the decision it informed.
- Small-slice percentages can move sharply because of one or two sessions. Raw counts and case inspection provide necessary context but do not turn a small sample into strong statistical evidence.
- LLM-generated sessions can enlarge a contrast or stress-test set but cannot recreate statistical independence once the real holdout has influenced design. Synthetic cases must be generated from explicit intent frames, split by product or intent before generation, checked for target leakage and label correctness, and reported separately from official-session results.
- Retaining negative and inconclusive results reduces repeated work and selective reporting. It also makes the sequence of design decisions and holdout exposure auditable.

The exact tuning/holdout sizes and any future synthetic-set construction remain experiment-design decisions. The evaluation governance, evidence layers, and reproducibility requirements are otherwise selected.

## Connections to the rest of the agent

- Information required from upstream capabilities: per-stage evidence, fixed inputs, configurations, traces, outputs, and failure categories from `SD-01` through `SD-10`.
- Information supplied to the design process: accepted or rejected hypotheses, selected parameter values, regression cases, revisit triggers, and evidence for the final conceptual agent.
- New questions created for the final area: how the chosen capabilities, state, control flow, and evaluation feedback form one coherent system.

## Architecture critic feedback

Awaiting user synthesis.

## Revisit conditions

Revisit when repeated tuning consumes the holdout, private performance diverges from public evidence, capability metrics fail to predict end-to-end outcomes, scenario slices are too small for stable conclusions, or operational limits become known.
