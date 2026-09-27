# ADR-008: Use raw TF-IDF in the final M3 route comparison

- Status: `Superseded by ADR-009 after the final M3 tuning comparison`
- Date: `2026-09-27`
- Supersedes: only the third-route choice in `ADR-007`; the LSA baseline remains
  available for reproducing the earlier vectorization experiment

## Context

On the fixed tuning sessions at depth 100, raw TF-IDF reached 0.35 recall,
compared with 0.2375 for SVD-256 and 0.1875 for SVD-64. Miss inspection showed
that many remaining failures came from under-specified first-turn queries and
many similarly suitable products, so broader semantic-retrieval conclusions are
deferred until multi-turn dialogue exists.

Raw TF-IDF is a sparse lexical representation, not a dense semantic embedding.
Calling it dense would hide the actual comparison being made.

## Decision

- Preserve the existing LSA implementation and its comparison experiment.
- Add a separately named `raw_tfidf` route using the same field-labelled catalog
  documents, 20,000-feature TF-IDF vocabulary, normalization, cosine similarity,
  and stable product-ID tie-breaking used in the diagnostic experiment.
- Replace the `dense` slot in the final M3 route-comparison runner with
  `raw_tfidf`, producing a clear lexical/facet/raw-TF-IDF comparison.
- Keep the same tuning split, first-turn queries, candidate depth, and reporting.
- The user runs and interprets the comparison. Do not use the holdout yet.

## Non-goals

- No neural embedding, multi-view representation, query reformulation, dialogue
  integration, route fusion, constraint filtering, or final route selection.
- No claim that raw TF-IDF is semantic dense retrieval.

## Revisit condition

After dialogue integration, evaluate retrieval again with later-turn queries.
Only then decide whether a neural dense or multi-view route is useful.

## Approval record

Accepted by the user's explicit instruction to run the final lexical, facet, and
raw-TF-IDF comparison on `2026-09-27`.
