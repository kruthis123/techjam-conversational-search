# ADR-014: M4 tuning boundary and adoption rule

- Status: `Accepted`
- Author: `User`
- Date: `2026-10-14`
- Decision area: M4 experiment governance
- Related design record: `SDR-011`
- Related milestone: `M4 — Candidate fusion and constraint-aware selection`

## Decision question

How should M4 preserve a protected holdout and choose a candidate cutoff without
post-result threshold selection?

## Decision

1. Retain the deterministic M3 scenario-stratified 80/20 membership for this
   fixed public set. All 200 target products are unique, so exact-target product
   grouping would still produce singleton groups.
2. Materialize tuning and holdout records once into separate files. The M4
   comparison runner accepts only the prepared tuning file and split manifest;
   it does not load or split the complete public set.
3. Record hashes and IDs for both partitions in the split manifest without
   exposing holdout records in the tuning report.
4. A cutoff qualifies only if it has zero false exclusions, zero contradiction
   leakage, and zero targets lost relative to the full route union. The user
   selects the smallest qualifying cutoff. If none qualifies, the decision is
   deferred for investigation.
5. The JSON report includes the split/input identities, deterministic split
   statement, exact command, Python and dependency versions, fixed route and
   fusion configuration, per-session evidence, and aggregate metrics.

## Alternatives considered

- Group by exact target product: rejected for M4 because every target occurs
  once and therefore provides no additional grouping boundary.
- Continue splitting inside the comparison runner: rejected because it reads
  and materializes the protected subset during ordinary tuning.
- Choose an acceptable recall loss after seeing results: rejected because it
  makes the adoption threshold movable.

## Consequences

- One small preparation step is required before the user-run experiment.
- The tuning command cannot accidentally evaluate the holdout through its
  normal interface.
- The cutoff rule favors recall preservation over candidate-count savings.
- A future dataset with repeated product or intent groups must revisit the split
  method rather than inherit this dataset-specific exception.

## Approval record

Accepted through the user's explicit approval of the four-part reconciliation
on `2026-10-14`.

## Experiment outcome

The user ran the tuning comparison and selected cutoff `300` provisionally on
`2026-10-20`. It was the smallest tested cutoff with zero target loss relative
to the full union, zero false exclusions, and zero contradiction leakage.

This choice must be revisited after dialogue integration. First-turn eligibility
excluded no candidates, so the experiment did not establish that `300` remains
necessary once later turns provide stronger constraints and queries.
