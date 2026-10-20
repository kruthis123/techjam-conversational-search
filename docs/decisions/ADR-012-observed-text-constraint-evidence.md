# ADR-012: Observed-text constraint evidence

- Status: `Accepted under M4 authorization`
- Date: `2026-10-09`
- Roadmap milestone: `M4 — Candidate fusion and constraint-aware selection`
- Related system-design records: `SDR-001`, `SDR-005`
- Related implementation ADRs: `ADR-003`, `ADR-011`

## Context

The simulator copies many requirements from catalog titles, features, details,
descriptions, categories, or store values. M4 needs a minimal reliable way to
confirm those requirements without turning missing text into a contradiction.

The raw catalog remains the factual source of truth. The current baseline has
no alias ontology, material-component model, unit conversion, or compatibility
table.

## Decision

- Compare one required observed claim against the raw `title`, `features`,
  `details`, `description`, `categories`, and `store` fields.
- Normalize both sides into case-folded word tokens and confirm a match only
  when the complete claim-token sequence occurs in one source field.
- Preserve the matching source-field name in the assessment reason.
- If the requirement has no usable value, return `unresolved`.
- If no exact observed sequence is found, return `unknown`, not a confirmed
  contradiction.
- Budget claims remain outside this comparator because numeric limits require
  relation-aware comparison.

This comparator confirms observed support. It does not infer synonyms,
equivalence, absence, component scope, or incompatibility.

## Alternatives considered

- Treat absence from the searched fields as contradiction. Rejected because
  incomplete metadata and wording variation would create false exclusions.
- Use substring matching. Rejected because short values such as `red` could
  match inside unrelated words.
- Add semantic similarity or an LLM. Deferred because similarity is not factual
  evidence and the simulator currently reuses catalog wording.
- Build typed comparators for every attribute immediately. Deferred under the
  learning-first requirement until experiment evidence shows which comparison
  gaps matter.

## Consequences

- Exact catalog-backed requirements can become confirmed matches.
- Non-matches remain provisional and cannot exclude a product.
- The source field makes positive evidence traceable.
- False negatives are expected for aliases and paraphrases, but they degrade to
  unknown rather than false contradiction.

## Revisit trigger

Revisit when the M4 experiment shows that important target constraints remain
unknown despite reliable differently worded catalog evidence.

## Approval record

Accepted under the user's instruction to proceed autonomously through M4 until
the experiment is ready on `2026-10-09`.
