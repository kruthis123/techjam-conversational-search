# ADR-010: Candidate union and reciprocal-rank fusion

- Status: `Accepted under M4 authorization`
- Date: `2026-09-28`
- Roadmap milestone: `M4 — Candidate fusion and constraint-aware selection`
- Related system-design records: `SDR-004`, `SDR-005`

## Context

The provisional retrieval routes return independent ranked lists whose scores
are not comparable. M4 needs one deduplicated candidate list while preserving
the evidence needed to understand why each product entered the pool.

The candidate cutoff and constraint-aware eligibility policy require separate
experiments. Combining them with fusion would make target loss harder to
attribute.

## Decision

- Merge route outputs by `parent_asin`.
- Preserve each contributing route's name, local rank, and local score.
- Compute the fused score with standard reciprocal-rank fusion:
  `sum(1 / (60 + route_rank))`.
- Use route-local ranks, not route scores, because BM25, facet, and SVD-256
  scores have different meanings and scales.
- Order candidates by descending fused score and use `parent_asin` as the
  deterministic tie-breaker.
- Return the complete fused union from this boundary. A later M4 task will own
  the configurable candidate cutoff and its user-run comparison.

The rank constant `60` is a simple conventional baseline, not an
experimentally selected optimum. It can be reopened if the cutoff experiment
shows that RRF ordering removes useful single-route candidates.

## Consequences

- A product returned by several routes receives accumulated support without
  being duplicated.
- Route evidence remains inspectable for later ranking and diagnostics.
- Fusion does not claim that a candidate meets any user constraint.
- Cutoff selection, eligibility classification, and final recommendation
  ranking remain outside this decision.

## Revisit trigger

Revisit the rank constant or fusion method if a target is present in the full
route union but RRF consistently places it below reasonable candidate cutoffs.

The M4 tuning experiment selected cutoff `300` provisionally on `2026-10-20`.
Lower tested cutoffs lost targets relative to the full union: 56 at 25, 42 at
50, 26 at 100, 12 at 150, and 2 at 200. Revisit the cutoff after dialogue
integration supplies later-turn queries; do not treat `300` as permanent.

## Approval record

Accepted under the user's explicit instruction to proceed to M4 on
`2026-09-28`.
