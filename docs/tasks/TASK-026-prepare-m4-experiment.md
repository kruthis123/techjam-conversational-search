# TASK-026: Prepare the M4 fusion and eligibility experiment

- Status: `Verified`
- Owner: `implementer`
- Roadmap milestone: `M4 — Candidate fusion and constraint-aware selection`
- Related accepted ADRs: `ADR-009`, `ADR-010`, `ADR-011`, `ADR-012`, `ADR-013`

## Goal

Produce a reproducible tuning-only JSON report that lets the user compare RRF
candidate cutoffs and inspect eligibility failures without automatically
selecting a winner.

## Inputs and outputs

Inputs:

- frozen catalog and public dataset paths;
- route depth, fixed to 100 for the documented M4 run;
- candidate cutoffs supplied on the command line;
- output JSON path.

Output: one JSON report containing aggregate metrics and per-session evidence.

## Allowed files

- `experiments/m4_compare_fusion_eligibility.py`
- `tests/test_m4_compare_fusion_eligibility.py`
- `docs/experiments/M4-fusion-eligibility-experiment.md`
- `docs/tasks/TASK-026-prepare-m4-experiment.md`
- `docs/PROJECT_STATE.md`

## Non-goals

- Running the experiment or selecting a cutoff for the user.
- Reading the protected holdout split.
- Simulating later dialogue turns.
- Comparing RRF constants or alternative fusion algorithms.
- Changing retrieval, comparison, eligibility, or ranking behavior.

## Fixed experiment design

- Use only the deterministic M3 tuning split.
- Use BM25, facet, and SVD-256 at route depth 100.
- Compare cutoffs `25`, `50`, `100`, `150`, `200`, and `300` in one run.
- Reconstruct the official first-turn message and pass only its parsed claims and
  query to retrieval and eligibility.
- Use target labels only after route outputs, fusion, and eligibility are
  complete for measurement.
- Do not automatically choose a cutoff. The user compares target survival and
  retained-candidate cost.
- Eligibility guardrails are fixed: false exclusions and contradiction leakage
  must both be zero before M4 can complete.

## Acceptance criteria

- Given one tuning session, when routes execute, then every route receives the
  same message-derived query and route depth.
- Given route outputs, when summarized, then the report records route target
  ranks, full-union presence, fused target rank, and target presence at every
  requested cutoff.
- Given all sessions, when summarized, then every cutoff reports target recall,
  targets lost relative to the full union, and mean candidate count.
- Given candidate eligibility results, when summarized, then every cutoff
  reports confirmed, provisional, ineligible, retained, false-exclusion, and
  contradiction-leakage counts.
- Given an exclusion, when recorded, then the candidate identity and
  contradiction assessment reasons remain inspectable.
- Given the command-line interface, when help is requested, then it documents
  the tuning-only boundary and all required inputs without loading the catalog.
- Given the experiment handoff, when read by the user, then it provides the
  exact command, output fields to inspect, decision questions, and completion
  evidence to report without claiming that the experiment was run.

## Test cases

- Synthetic target present in one route and below a small fused cutoff.
- Synthetic confirmed, provisional, and ineligible candidate results.
- Synthetic target falsely excluded by a contradiction.
- Empty route outputs.
- CLI help.

## Verification commands

```bash
unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest tests.test_m4_compare_fusion_eligibility -v
unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest discover -v
```

## Risks or assumptions

- This is a first-turn tuning experiment. Route retention and the cutoff may be
  revisited after dialogue integration supplies later-turn claims.
- The public target is a narrow recall proxy, not proof that every retained
  candidate is relevant.
- The holdout remains untouched because this task prepares parameter selection.

## Approval record

Approved under the user's instruction to proceed autonomously through M4 until
the experiment is ready on `2026-10-09`.

## Implementation evidence

- Shared first-turn retrieval inputs:
  `test_every_route_receives_the_same_query_and_depth` verifies that lexical,
  facet, and SVD-256 receive the same query and route depth. The runner reuses
  the deterministic M3 `stratified_split`, official simulator-message
  reconstruction, M2 parser, and retrieval-query builder, and fixes the CLI
  run to depth `100`.
- Trusted simulator-message boundary:
  `test_complete_path_separates_message_processing_from_target_scoring`
  verifies that trusted preparation emits an immutable message without a
  target field plus a separate scoring label; parsing, query construction,
  retrieval, and eligibility then execute from the prepared message without a
  sample or `ground_truth`, and the target label is supplied only to
  summarization.
- Route, union, fusion, and cutoff evidence:
  `test_records_route_union_fusion_and_cutoff_target_evidence` verifies
  route-local target ranks, full-union presence, fused target rank, target
  presence at every requested cutoff, target recall, losses relative to the
  full union, top-level sample count, per-route target recall, full-union
  target recall, mean candidate count, and mean retained candidate count.
- Eligibility metrics and inspectable exclusions:
  `test_summarizes_eligibility_and_false_exclusion_evidence` verifies
  confirmed, provisional, ineligible, retained, false-exclusion, and
  contradiction-leakage counts, plus excluded candidate identity and the
  preserved price contradiction reason.
- Empty retrieval boundary:
  `test_empty_route_outputs_produce_zero_counts` verifies absent target ranks
  and zero recall, candidate, and retained counts for empty route outputs.
- Tuning-only CLI:
  `test_cli_help_documents_tuning_only_required_inputs` verifies that help
  documents the tuning-only/no-holdout/no-selection boundary and required
  catalog, dataset, cutoff, and output arguments without loading data.
- User experiment handoff:
  `docs/experiments/M4-fusion-eligibility-experiment.md` records the exact
  six-cutoff command, output fields, decision questions, zero-tolerance
  guardrails, and completion evidence while explicitly stating that the
  catalog experiment has not been run and no cutoff has been selected.
- Focused verification passed 6/6 synthetic and CLI-help-only tests:
  `unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest tests.test_m4_compare_fusion_eligibility -v`.
- Full deterministic repository verification passed 108/108 tests:
  `unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest discover -v`.
- The actual catalog experiment and holdout evaluation were not run, and no
  result artifact was inspected or cutoff selected.

## Review findings and resolution

- Resolved: target-bearing samples previously reached the M4 processing path.
  `prepare_tuning_session` now isolates trusted official-message reconstruction
  and returns separate `PreparedMessage` and `ScoringLabel` values.
  `process_prepared_message` accepts no sample or target label, and
  `summarize_session` is the first downstream function to receive the label.
- Resolved: the report now includes top-level `sample_count`, per-route target
  recall, and full-union target recall.
- Resolved: every cutoff now includes `mean_retained_candidate_count` alongside
  pre-eligibility mean candidate count.
- Acceptance verification passed all seven task criteria with focused `6/6`
  and full `108/108` deterministic tests.
- Resolved by `ADR-014` and `TASK-027`: the accepted deterministic membership is
  materialized into separate tuning and protected-holdout files before ordinary
  tuning; the runner accepts only the prepared tuning file and split manifest.
- Resolved by `ADR-014` and `TASK-027`: the user selects the smallest cutoff with
  zero false exclusions, zero contradiction leakage, and zero target loss
  relative to the full union, or defers when none qualifies.
- Resolved by `TASK-027`: the report records the required split/input hashes,
  deterministic split statement, command, environment, fixed configuration,
  per-session evidence, and aggregates.
- Independent review and acceptance verification of `TASK-027` confirmed that
  the reconciliation closes the remaining governance findings.
