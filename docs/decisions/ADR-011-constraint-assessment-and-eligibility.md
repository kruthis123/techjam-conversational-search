# ADR-011: Constraint assessment and eligibility representation

- Status: `Accepted under M4 authorization`
- Date: `2026-10-09`
- Roadmap milestone: `M4 — Candidate fusion and constraint-aware selection`
- Related system-design records: `SDR-005`
- Related implementation ADRs: `ADR-010`

## Context

Typed catalog comparators must eventually report whether each hard constraint
is confirmed, contradicted, or uncertain. Eligibility aggregation and later
ranking need this evidence without coupling themselves to category, price, or
future comparator details.

`SDR-005` already fixes the system policy: one confirmed contradiction makes a
candidate ineligible; all confirmed matches make it confirmed; every other
non-contradictory combination remains provisional.

## Decision

- Represent one comparison as an immutable constraint assessment containing:
  the attribute, one assessment state, and a traceable reason.
- Preserve these states separately: `confirmed_match`,
  `confirmed_contradiction`, `unknown`, `inferred`, `ambiguous`, and
  `unresolved`.
- Represent the result as the original fused candidate, its eligibility status,
  and all assessments. The eligibility statuses are `confirmed`,
  `provisional`, and `ineligible`.
- Aggregate assessments deterministically:
  - any `confirmed_contradiction` produces `ineligible`;
  - only `confirmed_match` assessments produce `confirmed`;
  - any non-contradictory uncertainty state produces `provisional`.
- A candidate with no active hard-constraint assessments is `confirmed`
  because there is no hard requirement left to prove or contradict.
- Keep comparison logic outside the aggregator. Category and price comparators
  will create these assessments in later tasks.

The reason is descriptive evidence for learning and diagnostics, not a value
used to determine eligibility.

## Alternatives considered

- Collapse all uncertainty into one `unknown` state. This is smaller but loses
  the accepted distinction between inferred, missing, ambiguous, and unresolved
  evidence that later ranking and diagnostics may use.
- Store a generic evidence graph or confidence score. This adds machinery not
  required by the fixed catalog, accepted policy, or current experiment.
- Let each comparator return a final candidate status. This would duplicate the
  multi-constraint aggregation policy and make inconsistent exclusions easier.

## Consequences

- Comparator tasks can remain small and typed while sharing one aggregation
  rule.
- Ineligible candidates retain the exact assessment that caused exclusion.
- Retrieval evidence remains attached through the original fused candidate.
- The representation does not itself decide whether catalog evidence is
  reliable enough to create a confirmed match or contradiction; each typed
  comparator owns that decision.

## Deferred work

- Category and numeric-price comparison.
- Material, component, dimensional compatibility, aliases, and unit conversion.
- Ordering confirmed versus provisional candidates, which belongs to M5.

## Approval record

Accepted under the user's M4 authorization and explicit instruction to proceed
on `2026-10-09`.
