# ADR-003: Raw product and derived-claim boundary

- Status: `Accepted`
- Author: `User`
- Date: `2026-09-17`
- Decision area: `M1 catalog truth, identity, normalization, and provenance`
- Related learning cards: `LC-01`, `LC-05`
- Related system-design records: `SDR-001`, `SDR-005`, `SDR-012`
- Official requirement references: `docs/competition_specification.md`, `docs/agent_api_contract.json`

## Decision question

What stable implementation boundary should preserve an authoritative raw catalog product while allowing later normalized claims to carry source evidence and provenance?

## Scope and non-goals

In scope:

- product identity and raw-record ownership;
- whether downstream code receives raw mappings directly or through an observed-product envelope;
- separation between observed fields and derived claims;
- minimum provenance information needed to trace a derived claim to raw evidence.

Not decided here:

- the actual facet vocabulary, aliases, unit conversions, or compatibility rules;
- lexical or dense index schemas;
- persistence technology;
- candidate, ranking, dialogue, or diagnostic records;
- inferred LLM-generated product claims.

## Contract facts and existing decisions

Official facts:

- `parent_asin` is the scored product identifier.
- Catalog-visible fields are `parent_asin`, `title`, `features`, `description`, `price`, `categories`, `details`, `average_rating`, `rating_number`, and `store`.
- The frozen catalog is expected to contain 50,000 JSONL records.

Accepted system-design decisions:

- raw catalog fields remain factual truth;
- original text remains available;
- derived representations remain linked to source evidence;
- provenance belongs to individual claims or relationships;
- observed, normalized, inferred, unknown, and similarity evidence have different downstream authority;
- deterministic accepted normalization may confirm a value only when it preserves and traces to raw meaning.

Catalog evidence collected on `2026-09-17`:

- `data/catalog.jsonl` contains 50,000 parseable records and 50,000 unique, non-empty `parent_asin` values.
- Every record contains exactly the ten documented fields.
- `features`, `description`, and `categories` are lists; `details` is a dictionary.
- `price` is null in 39,473 records, a float in 10,410, and a string in 117.
- `store` is a string in 49,686 records and null in 314.
- The weak evaluator reproduced the recorded baseline under Python 3.12.

These variations make preservation preferable to early canonical coercion.

## Inputs, outputs, ownership, and invariants

Input: one verified raw catalog JSON object.

Outputs:

- a trustworthy product identity;
- preserved raw observed evidence;
- later, zero or more separate derived claims carrying provenance.

Invariants:

- no normalization mutates or overwrites raw evidence;
- every product is addressed by its non-empty `parent_asin`;
- duplicate identities and malformed records are surfaced rather than silently merged;
- every normalized claim can identify its source field and raw evidence;
- missing evidence remains distinguishable from contradiction;
- retrieval similarity never becomes a factual product claim.

## Failure cases

- a typed product model drops an unexpected raw field or coerces a value incorrectly;
- direct mutable mappings allow a normalizer to overwrite factual input;
- derived values lose their source field or evidence span/value;
- two records share a `parent_asin` and are silently combined;
- a missing field is represented as a negative fact;
- one universal confidence score erases the difference between normalized and inferred evidence.

## What I need to research

- Questions I must answer:
  - Does the actual frozen catalog have stable enough field shapes for a typed observed-product envelope?
  - Which minimum source locator is sufficient for dictionaries, lists, and free text?
  - Does the first loader task need any claim type, or can claim representation wait for the normalization task?
- Sources or evidence needed:
  - verified samples and a field-shape audit from `data/catalog.jsonl`;
  - accepted provenance requirements in `SDR-001` and evidence rules in `SDR-005`;
  - downstream information needs named in the M1 normalization audit.

## Decision criteria

- fidelity to raw catalog evidence;
- traceability of derived claims;
- ability to distinguish missing, observed, normalized, inferred, and conflicting evidence;
- simple catalog loading and deterministic tests;
- resistance to schema drift and irregular raw values;
- usefulness across constraints, retrieval, ranking, dialogue, and diagnostics without forcing their implementation now.

## Options I considered

| Option | How it works | Strengths | Failure modes and trade-offs | Evidence |
|---|---|---|---|---|
| Preserved raw mapping plus separate derived-claim collection | Loader retains each parsed JSON object as the observed record; later normalizers emit separate claim objects keyed by `parent_asin` and source locator | Lowest risk of dropping raw information; simple first loader; derived evidence cannot masquerade as raw fields | Weaker static typing at the raw boundary; downstream access must be disciplined; mutation protection must be explicit | Strongly compatible with `SDR-001`; actual catalog shape still needed |
| Typed observed-product envelope retaining the complete raw mapping | Stable known fields receive typed accessors while the full raw object remains attached; derived claims remain separate | Clearer field contracts and typing while preserving raw evidence | Duplicates representation; coercion and synchronization rules can drift; unknown catalog shapes may complicate the model | Requires catalog field-shape audit |
| Typed canonical product replaces the raw mapping | Loader coerces the catalog into one canonical product model used everywhere | Convenient downstream access | Can lose text, unexpected fields, ambiguity, and original values; normalization can become indistinguishable from observation | Conflicts with the accepted raw-source-of-truth boundary and is not viable |

## Validation experiments

This decision needs a deterministic catalog-shape audit, not a ranking experiment.

- Hypothesis: the chosen boundary preserves every raw record and supports traceable claims without silent coercion.
- Fixed inputs: verified catalog plus a fixed sample containing missing values, dictionaries, lists, numeric fields, and unusual shapes.
- Alternatives compared: raw mapping with separate claims versus typed envelope with complete raw mapping.
- Measurement: raw round-trip fidelity, identity validation, field-shape coverage, provenance traceability, and implementation complexity.
- Success or decision threshold: zero silent raw-field loss or identity merges; every sample claim traces to a raw field/value; irregular records produce explicit diagnostics.
- Result: the catalog audit found a stable top-level field set but meaningful value-type and missingness variation. Preserving raw mappings avoids coercion and duplication; separate derived claims preserve provenance and authority boundaries.

## Questions I must answer before deciding

Resolved on `2026-09-17`:

1. The user delegated the choice to the option that is more efficient and least likely to corrupt the source of truth.
2. Choose preserved raw mappings with separate derived claims.
3. Keep the first task limited to raw loading and identity validation; introduce the derived-claim representation in the following normalization task where its evidence needs can be tested.

## My proposed decision

Use a catalog-owned mapping from `parent_asin` to the complete parsed raw record. Treat those records as read-only factual evidence. Normalization must emit separate derived claims rather than adding to, replacing, or coercing raw fields.

The first task implements only raw loading, identity validation, and preservation. A later M1 ADR/task will define claim fields and provenance locators using the normalization audit.

## Architecture critic feedback

Not requested. The catalog audit and accepted system-design constraints distinguish the viable options without changing the conceptual agent.

## My final decision

Accepted under the user's delegated decision criteria on `2026-09-17`:

- preserve each complete parsed raw mapping without field coercion;
- index catalog ownership by unique `parent_asin`;
- treat catalog-owned raw records as read-only;
- store all future normalized or inferred claims separately with claim-level provenance;
- implement only loading and identity validation in the first task.

## Why I chose it and evidence used

- It performs one parse and stores one authoritative raw representation rather than duplicating typed fields.
- It cannot silently desynchronize a typed copy from the raw source.
- It preserves nulls, strings, numbers, lists, dictionaries, and original text exactly as parsed.
- The actual catalog has stable keys but mixed `price` types and nullable values, making early coercion an avoidable risk.
- Separate claims directly implement `SDR-001`'s authority and provenance boundary.

## Rejected alternatives and why

- A typed observed-product envelope was rejected for the baseline because it duplicates access to stable fields and introduces coercion or synchronization rules without current evidence of a compensating benefit.
- A canonical-product-only model is incompatible with the accepted requirement to preserve raw catalog truth.
- A typed envelope may be reconsidered if repeated access defects or measurable maintenance cost appear.

## Consequences and trade-offs I accept

- Raw field access has weaker static typing.
- Read-only ownership is an enforced module invariant and review concern rather than a conversion into a different canonical shape.
- Downstream capabilities must not annotate raw records; they consume them and emit separate evidence.
- The claim and provenance structure remains a later decision because the loader task does not need it.

## Interfaces or invariants this decision creates

- Catalog loading returns identity-addressable raw mappings.
- Raw values are not normalized or coerced during loading.
- Missing fields, malformed rows, empty identities, and duplicate identities are reported rather than repaired or merged.
- Derived claims never overwrite or masquerade as raw catalog fields.

## Compatibility check

- Official contract: preserves `parent_asin` identity and catalog-valid recommendation grounding.
- `SDR-001`: must preserve raw truth and claim-level provenance.
- `SDR-005`: must support match, contradiction, and abstention without treating missing as negative.
- M1 normalization audit: must trace aliases, units, component scope, compatibility, conflicts, and missing values.

## Revisit trigger

Revisit if real catalog irregularities cannot be represented without loss, or later capabilities need source localization not supported by the accepted provenance boundary.
