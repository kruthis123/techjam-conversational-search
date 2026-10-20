# ADR-013: Explicit budget-ceiling evidence

- Status: `Accepted under M4 authorization`
- Date: `2026-10-09`
- Roadmap milestone: `M4 — Candidate fusion and constraint-aware selection`
- Related system-design records: `SDR-005`
- Related implementation ADRs: `ADR-004`, `ADR-011`

## Context

Numeric catalog prices are reliable observed evidence for 10,410 products.
They can support a confirmed match or contradiction when the user expresses an
explicit upper-bound relation. Missing and unsupported string prices must
remain unknown.

The simulator can also say `budget around $X`. “Around” does not define an
upper bound, so converting it into one would invent stricter intent.

## Decision

- Support three explicit upper-bound forms: `under X`, `up to X`, and `<= X`,
  with an optional dollar sign and optional decimal amount.
- Interpret `under X` strictly as product price `< X`.
- Interpret `up to X` and `<= X` inclusively as product price `<= X`.
- A supported numeric price inside the bound produces `confirmed_match`; a
  supported numeric price outside it produces `confirmed_contradiction`.
- Missing, null, boolean, and string catalog prices produce `unknown`.
- Budget wording without a supported upper-bound relation, including
  `budget around X`, produces `unresolved`.
- Assessment reasons record the raw `price` source and the compared values.

## Alternatives considered

- Treat `budget around X` as a ceiling. Rejected because it changes approximate
  intent into a hard maximum.
- Parse every price relation and currency. Deferred because the fixed baseline
  needs only a small inspectable comparator.
- Treat missing price as contradiction. Rejected because absence is not proof
  that the product exceeds the budget.

## Consequences

- Explicit budget violations become the first reliable exclusion path.
- Unsupported budget language and catalog prices remain provisional.
- The experiment can measure false exclusions at strict and inclusive numeric
  boundaries without adding a general numeric-expression parser.

## Revisit trigger

Revisit when the experiment shows that unresolved budget wording materially
affects target survival or retained candidate counts.

## Approval record

Accepted under the user's instruction to proceed autonomously through M4 until
the experiment is ready on `2026-10-09`.
