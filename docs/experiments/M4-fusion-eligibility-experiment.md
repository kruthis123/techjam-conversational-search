# M4 experiment: Compare fusion cutoffs and eligibility

## Status and decision owner

The split and runner are implemented and deterministically tested. The user ran
the tuning comparison and selected cutoff `300` provisionally on `2026-10-20`.
The protected holdout was not evaluated.

The prepared tuning file and protected holdout are physically separate. The
comparison command is bound to canonical `data/m4_tuning.jsonl` and
`data/m4_split_manifest.json`; it cannot accept another dataset or manifest
through its normal interface.

## Fixed design

- Routes: lexical BM25, facet, and SVD-256.
- Shared first-turn query: reconstructed through the existing official-message,
  M2 parsing, and retrieval-query path.
- Trusted boundary: hidden simulator data prepares an immutable message and a
  separate scoring label. Parsing, query construction, retrieval, fusion, and
  eligibility receive only the prepared message and catalog-derived inputs;
  the target label enters only during result summarization.
- Route depth: `100` for every route.
- Fusion: the accepted RRF implementation with rank constant `60`.
- Cutoffs compared together: `25`, `50`, `100`, `150`, `200`, and `300`.
- Eligibility: required claims only, using the accepted observed-text and
  explicit budget-ceiling comparators.
- Target labels are used only after retrieval, fusion, cutoff, and eligibility
  processing to measure outcomes.
- The runner records source, tuning, holdout, and catalog identities and hashes;
  exact command; Python and scikit-learn versions; fixed route/fusion settings;
  per-session evidence; and aggregates.
- The runner reports evidence and never selects a cutoff.

## One-time split preparation

The split artifacts have been generated with:

```bash
.venv/bin/python -m experiments.prepare_m4_split \
  --source data/public_set.jsonl \
  --tuning-output data/m4_tuning.jsonl \
  --holdout-output secure/m4_holdout.jsonl \
  --manifest-output data/m4_split_manifest.json
```

This produces 160 tuning sessions, 40 protected holdout sessions, and a tracked
manifest containing partition membership and SHA-256 hashes. The holdout file
is ignored by Git. Do not pass it to the M4 comparison command.

## Exact tuning command

Run this only when you are ready to perform the user-owned M4 experiment:

```bash
unset VIRTUAL_ENV && uv run --python 3.12 python -m experiments.m4_compare_fusion_eligibility \
  --catalog data/catalog.jsonl \
  --cutoffs 25 50 100 150 200 300 \
  --output /tmp/m4-fusion-eligibility-tuning.json
```

The command writes the JSON report to
`/tmp/m4-fusion-eligibility-tuning.json` and also prints it to standard output.

## Report fields to inspect

Top-level fields:

- `split`: must be `tuning`.
- `sample_count`: number of tuning sessions summarized.
- `route_depth`: must be `100`.
- `route_names`: must contain `lexical`, `facet`, and `svd_256`.
- `route_target_recall`: target recall for each provisional route.
- `full_union_target_recall`: target recall in the complete route union.
- `cutoffs`: aggregate measurements keyed by cutoff.
- `sessions`: per-session trace evidence.
- `reproducibility`: split and input hashes, deterministic split statement,
  exact command, environment versions, and fixed route/fusion configuration.

For each cutoff, inspect:

- `target_recall`;
- `targets_lost_relative_to_full_union`;
- `mean_candidate_count`;
- `mean_retained_candidate_count`;
- `confirmed_count`, `provisional_count`, and `ineligible_count`;
- `retained_count`;
- `false_exclusion_count`;
- `contradiction_leakage_count`.

For individual failures, inspect each session's:

- `query` and `route_target_ranks`;
- `full_union_contains_target` and `fused_target_rank`;
- cutoff-specific `target_present` and `target_retained`;
- `excluded` entries, which retain candidate IDs and contradiction reasons.

## Decision questions for the user

1. Which cutoffs have zero false exclusions, zero contradiction leakage, and
   zero targets lost relative to the full union?
2. Select the smallest cutoff that satisfies all three conditions. If none
   qualifies, defer the cutoff and investigate without weakening the rule.
3. How much mean candidate-assessment cost is saved at each smaller cutoff,
   and how many candidates remain after eligibility on average?
4. Are losses caused by route coverage, RRF position, or eligibility exclusion?
5. Do any scenarios show systematic exact-text false negatives that should be
   investigated before accepting the baseline?

Do not choose a cutoff unless all three predeclared conditions are satisfied.
Record affected session IDs, candidate IDs, and contradiction reasons first.

## Completion evidence to report

After running and interpreting the experiment, report:

- the exact command and output path;
- `sample_count`, per-route target recall, full-union target recall, and the six
  cutoff keys;
- the aggregate metrics listed above for every cutoff;
- every false-exclusion or contradiction-leakage trace, or explicit evidence
  that both counts are zero at every cutoff;
- the user's keep/change/defer decision and rationale;
- any accepted limitation or follow-up task;
- confirmation that no holdout evaluation was run.

The evidence and user decision are recorded below; M4 is complete with a
provisional cutoff that must be revisited after dialogue integration.

## Result — 2026-10-20

Artifact: `tmp/m4-fusion-eligibility-tuning.json`

Artifact SHA-256:
`f82db01d4ce2adbc863f85aceb134e5278f0a87771bd225f5ef6a744f1556f5a`

Recorded command:

```bash
uv run --python 3.12 python -m experiments.m4_compare_fusion_eligibility \
  --catalog data/catalog.jsonl \
  --cutoffs 25 50 100 150 200 300 \
  --output /Users/kruthishivakumar/Workspace/github/techjam-conversational-search/tmp/m4-fusion-eligibility-tuning.json
```

The tuning set contained 160 sessions. Route target recall was `0.5125` for
lexical, `0.4125` for facet, and `0.2375` for SVD-256. Full-union target recall
was `0.60625`, or 97 of 160 targets.

| Cutoff | Target recall | Targets lost vs union | Mean candidates | False exclusions | Contradiction leakage |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 25 | 0.25625 | 56 | 25.0 | 0 | 0 |
| 50 | 0.34375 | 42 | 50.0 | 0 | 0 |
| 100 | 0.44375 | 26 | 100.0 | 0 | 0 |
| 150 | 0.53125 | 12 | 149.56875 | 0 | 0 |
| 200 | 0.59375 | 2 | 195.25625 | 0 | 0 |
| 300 | 0.60625 | 0 | 216.65625 | 0 | 0 |

Cutoff `300` was the smallest tested cutoff satisfying all three predeclared
conditions. The user selected it provisionally. Cutoff `200` lost targets for
`public_0094` and `public_0146`, whose fused ranks were 202 and 212.

Eligibility marked no candidate ineligible at any cutoff. Consequently, mean
retained count equaled mean candidate count. This run therefore established the
fusion cutoff but did not provide real-session evidence about contradiction
filtering beyond the deterministic focused tests.

Revisit cutoff `300` after dialogue integration supplies later-turn constraints
and stronger queries. Rerun the cutoff comparison rather than carrying `300`
forward as a permanent setting.
