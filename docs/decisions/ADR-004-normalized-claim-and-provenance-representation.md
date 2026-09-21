# ADR-004: Minimal source-linked price claim

- Status: `Accepted`
- Author: `User`
- Date: `2026-09-18`
- Decision area: `M1 catalog truth, identity, normalization, and provenance`
- Related system-design records: `SDR-001`, `SDR-005`, `SDR-012`
- Related accepted ADRs: `ADR-003`
- Official requirement references: `docs/competition_specification.md`

## Decision question

What is the smallest understandable representation that can test one normalized catalog facet without mutating the raw source?

## Context

The user explicitly wants a learning implementation that is as short and readable as possible. Hypothetical edge cases and reusable frameworks should be deferred until an experiment demonstrates their value.

The fixed catalog contains:

- 10,410 numeric prices;
- 39,473 null prices;
- 112 em-dash strings;
- five `from N.NN` strings.

`ADR-003` already requires raw records to remain authoritative and derived values to remain separate.

## Scope and non-goals

In scope:

- one simple derived price claim;
- a direct link to the raw `price` field;
- abstention when the raw value is not numeric;
- one catalog-scale count experiment.

Not in scope:

- a general-purpose claim framework;
- relation, unit, component, confidence, evidence-kind, or nested source-path models;
- lower-bound string parsing;
- material, color, size, dimensions, or compatibility;
- indexes, persistence, candidate filtering, ranking, or Agent integration;
- exhaustive malformed-input validation.

## Options considered

| Option | Benefit | Cost | Decision |
|---|---|---|---|
| General atomic claim model | May be reusable across future facets | Introduces several fields and semantics before they are exercised | Deferred |
| Attribute-centered facet bundles | Direct attribute lookup | Still requires nested provenance and conflict rules later | Deferred |
| Small task-specific price claim | Very short and directly testable | May need refactoring when a second facet is added | Selected |

## Final decision

Accepted through the user's simplification direction on `2026-09-18`:

- Implement one small immutable `PriceClaim` containing only `parent_asin`, numeric `value`, and `source_field`.
- `source_field` is the literal `price`, linking the claim to the preserved raw record.
- Keep the raw numeric value as an `int` or `float`; do not add `Decimal` conversion yet.
- A function accepts a trusted raw record from the verified catalog loader and returns either one `PriceClaim` or `None`.
- Numeric `int` or `float` price produces a claim. Boolean values do not.
- Missing, null, and string prices return `None`; absence means unknown or unsupported for this experiment.
- Do not revalidate `parent_asin`; `TASK-001` already owns catalog identity validation.
- Do not implement hypothetical invalid numeric cases that do not occur in the fixed catalog.
- Keep lower-bound strings and a general claim model as later experiment choices.

## Why this choice

- It tests the important boundary: derived evidence remains separate and traceable to raw catalog truth.
- It can be understood in one short file without introducing unused concepts.
- It creates a measurable result: 10,410 products should emit a price claim.
- It deliberately leaves a refactoring decision for the second facet, when there is evidence to compare a task-specific type against a generic claim representation.

## Consequences accepted

- Currency and exact/lower-bound semantics are implicit for this first experiment.
- Future facets may show that `PriceClaim` should be replaced by a general claim type.
- Unsupported strings are ignored rather than parsed.
- The implementation is not intended to be production-hardened.

## Invariants

- Raw records are not modified.
- A claim always points back to the raw `price` field.
- No claim is stronger than its raw evidence.
- Missing or unsupported evidence does not become a negative fact.

## Experiment

- Run the function over the fixed 50,000-product catalog.
- Measure the emitted claim count; expected baseline: 10,410.
- Inspect a few numeric, null, em-dash, and `from N.NN` examples.
- Use this implementation as the simple baseline when a second facet motivates comparing representation alternatives.

## Revisit trigger

Revisit when implementing a second facet, when a downstream capability needs explicit relation/unit/evidence fields, or when an observed failure shows that string-price semantics matter.

## M1 experiment result

On `2026-09-21`, the user chose to keep string prices unsupported and retain the separate `PriceClaim` representation. No implementation change is required. Revisit only if later evidence shows that the five lower-bound string prices or a shared downstream interface materially matter.
