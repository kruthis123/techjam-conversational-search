# ADR-005: Minimal normalized category claim

- Status: `Accepted by user experiment`
- Author: `Codex under user-delegated implementation authority`
- Date: `2026-09-18`
- Decision area: `M1 catalog truth, identity, normalization, and provenance`
- Related system-design record: `SDR-001`
- Related accepted ADRs: `ADR-003`, `ADR-004`

## Decision question

What is the smallest second facet that demonstrates normalization and can later support retrieval without introducing a general claim framework?

## Evidence

The fixed catalog contains 238,403 category entries. Every entry is a non-empty string. Normalizing with `strip().casefold()` and removing repeated values within one product leaves 238,277 category claims. Category is also an allowed dialogue attribute and a planned retrieval route.

## Options considered

| Option | Benefit | Cost | Decision |
| --- | --- | --- | --- |
| General claim type shared with price | Reuses one representation | Adds attribute and mixed-value semantics before downstream code needs them | Deferred to the user's M1 experiment |
| Material extracted from `details` | Useful for constraints | Only 2,069 records expose the exact `Material` key and aliases need additional policy | Deferred |
| Category-specific claim | Complete fixed-data coverage, simple normalization, useful for retrieval | Introduces a second small task-specific type | Selected as the baseline |

## Final decision

- Add an immutable `CategoryClaim` with `parent_asin`, normalized string `value`, and `source_field="categories"`.
- Produce claims in source order using `strip().casefold()`.
- Remove repeated normalized values within a product while preserving first occurrence.
- Keep the raw category list unchanged.
- Trust the verified fixed catalog shape; do not add validation for hypothetical non-string or empty category entries.
- Keep price and category claims separate for the baseline. The user will decide after the M1 experiment whether a general claim type would make the system clearer.

## Why this is the simplest useful baseline

It demonstrates actual normalization, preserves a direct source link, covers the full catalog, and supplies a facet that M3 retrieval can use. It avoids alias dictionaries, taxonomy construction, and irregular nested-detail extraction.

## Revisit trigger

Revisit only after the user completes the M1 experiment or a later capability requires one common claim interface.

## Authorization record

Selected and recorded under the user's explicit `Implement M1` authorization on `2026-09-18`. This selects a simple implementation baseline; it does not decide the later comparison experiment.

## M1 experiment result

On `2026-09-21`, the user chose to keep repeated categories deduplicated and retain the separate `CategoryClaim` representation. The user found the provenance understandable because the claim maps directly to the raw product's `categories` JSON key. No implementation change is required.
