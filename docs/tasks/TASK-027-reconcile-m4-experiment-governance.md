# TASK-027: Reconcile the M4 experiment boundary

- Status: `Verified`
- Owner: `implementer`
- Roadmap milestone: `M4 — Candidate fusion and constraint-aware selection`
- Related accepted ADRs: `ADR-009`, `ADR-010`, `ADR-011`, `ADR-012`, `ADR-013`, `ADR-014`

## Goal

Make the existing M4 comparison runnable from an isolated tuning file with a
complete reproducibility manifest and the predeclared cutoff rule.

## Inputs and outputs

Inputs:

- frozen `data/public_set.jsonl` used only by one-time split preparation;
- frozen catalog;
- the accepted deterministic scenario-stratified split rule;
- the six M4 cutoffs.

Outputs:

- physically separate tuning and protected-holdout JSONL files;
- a split manifest containing partition IDs and hashes;
- a tuning-only M4 JSON report with reproducibility metadata;
- an updated user experiment handoff.

## Allowed files

- `experiments/prepare_m4_split.py`
- `experiments/m4_compare_fusion_eligibility.py`
- `tests/test_prepare_m4_split.py`
- `tests/test_m4_compare_fusion_eligibility.py`
- `data/m4_tuning.jsonl`
- `data/m4_split_manifest.json`
- `secure/m4_holdout.jsonl` (local protected artifact; ignored by Git)
- `docs/experiments/M4-fusion-eligibility-experiment.md`
- `docs/tasks/TASK-026-prepare-m4-experiment.md`
- `docs/tasks/TASK-027-reconcile-m4-experiment-governance.md`
- `docs/PROJECT_STATE.md`

## Non-goals

- Running the M4 comparison or inspecting its metrics.
- Evaluating or exposing holdout contents.
- Choosing a cutoff for the user.
- Changing retrieval, fusion, eligibility, or constraint behavior.
- Generalizing the split utility beyond this fixed dataset.

## Acceptance criteria

- Given the fixed public set, when split preparation runs, then it writes the
  accepted deterministic memberships to separate tuning and holdout files and
  records their IDs and SHA-256 hashes in a manifest.
- Given the M4 comparison CLI, when it runs, then it accepts only the prepared
  tuning file and manifest and never loads or repartitions the complete public
  set or protected holdout.
- Given a mismatched tuning file or manifest, when comparison setup validates
  them, then it stops before retrieval with a clear error.
- Given a completed synthetic report, when serialized, then its manifest records
  split/input hashes, deterministic split statement, exact command, Python and
  scikit-learn versions, and fixed route/fusion configuration.
- Given cutoff aggregates, when the handoff is read, then it predeclares zero
  false exclusions, zero contradiction leakage, and zero loss relative to the
  full union, with the smallest qualifying cutoff selected by the user and
  deferral when none qualifies.
- Given task verification, when all checks finish, then no M4 catalog comparison
  or holdout evaluation has run and no cutoff has been selected.

## Test cases

- Deterministic synthetic split with scenario coverage.
- Manifest IDs and hashes match both prepared files.
- Comparison accepts a matching tuning file/manifest.
- Comparison rejects a mismatched tuning file/manifest before retrieval.
- Synthetic report contains the required reproducibility fields.
- CLI help and experiment handoff expose the tuning-only boundary and frozen
  cutoff rule.

## Verification commands

```bash
unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest tests.test_prepare_m4_split tests.test_m4_compare_fusion_eligibility -v
unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest discover -v
git diff --check
```

## Risks or assumptions

- Exact-target grouping is uninformative because the fixed public set has 200
  distinct targets across 200 sessions.
- `secure/m4_holdout.jsonl` remains local and ignored; its hash and membership,
  not its records, are retained in the tracked manifest.
- This task prepares the user experiment but does not execute it.

## Approval record

Approved by the user's explicit approval of the proposed reconciliation on
`2026-10-14`, under the standing M4 implementation authorization.

## Implementation evidence

- `experiments/prepare_m4_split.py` reuses the accepted M3 deterministic split
  and writes separate tuning and protected-holdout JSONL files plus a manifest
  containing source and partition counts, IDs, paths, and SHA-256 hashes.
- The generated artifacts contain 160 tuning and 40 holdout sessions.
  `secure/m4_holdout.jsonl` is ignored by Git; its records were not copied into
  documentation or a report.
- The normal comparison CLI has no tuning or manifest path arguments. It is
  bound to canonical `data/m4_tuning.jsonl` and
  `data/m4_split_manifest.json`, and the manifest must declare the canonical
  public-set, tuning, and protected-holdout paths before loading samples or the
  catalog. The runner no longer imports or calls the public-set split function.
- `load_prepared_tuning` additionally verifies the accepted split identity,
  distinct source/tuning/holdout paths and hashes, disjoint partition IDs,
  tuning SHA-256, ordered IDs, and count.
- The report's `reproducibility` object records split identity, method,
  deterministic seed statement, source/tuning/holdout/catalog hashes and IDs,
  exact command, Python and scikit-learn versions, and fixed route depth, route
  names, RRF constant, fusion method, and cutoffs.
- The experiment handoff fixes the adoption rule: the user selects the smallest
  cutoff with zero false exclusions, zero contradiction leakage, and zero loss
  relative to the full union; otherwise the decision is deferred.
- Focused verification passed `11/11` tests:
  `unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest tests.test_prepare_m4_split tests.test_m4_compare_fusion_eligibility -v`.
- Full deterministic verification passed `113/113` tests:
  `unset VIRTUAL_ENV && uv run --python 3.12 python -m unittest discover -v`.
- `git diff --check` passed with no output.
- No M4 catalog comparison or holdout evaluation was run, and no cutoff was
  selected.

## Review findings and resolution

- Resolved remaining high-priority finding: the normal CLI no longer exposes
  `--tuning` or `--manifest`; it uses canonical constants and rejects a manifest
  that relabels either `data/public_set.jsonl` or
  `secure/m4_holdout.jsonl` as tuning, even when the split ID, paths, hashes,
  and memberships are otherwise internally consistent.
- Focused boundary tests also retain coverage for the accepted split identity,
  distinct paths and hashes, disjoint memberships, and prepared-tuning hash,
  ordered-ID, and count validation before sample or catalog processing.
- Independent review found no remaining actionable findings.
- Independent acceptance verification passed all `6/6` criteria, with focused
  `11/11`, full `113/113`, and `git diff --check` passing.
