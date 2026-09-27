# ADR-007: Minimal retrieval route baselines

- Status: `Accepted under M3 authorization`
- Author: `Codex under user-delegated implementation authority`
- Date: `2026-09-22`
- Decision area: `M3 baseline catalog representations and retrieval routes`
- Related system-design records: `SDR-001`, `SDR-004`, `SDR-012`

## Decision question

What are the smallest useful lexical, facet, and dense retrieval baselines that can be compared on the same current user intent?

## Evidence and boundaries

The fixed catalog has roughly 50,000 products. M1 preserves raw catalog fields and derives trustworthy category claims. M2 exposes one active claim per user-intent attribute. SQLite FTS5 is available in the pinned Python runtime, while the current environment has no numerical or embedding library installed.

M3 measures candidate coverage only. Fusion, hard-constraint filtering, and final ranking belong to later milestones.

## Options considered

| Route | Options | Decision |
| --- | --- | --- |
| Lexical | Hand-written token overlap; SQLite FTS5 BM25; external search server | Use local SQLite FTS5 BM25 for a fielded lexical baseline without a service dependency. |
| Facet | Raw substring matching; normalized category-token index; inferred product facets | Use an inverted index over M1 normalized category claims, the only currently trustworthy nonnumeric facet. |
| Dense | Hosted embeddings; downloaded neural model; hashed token vectors; TF-IDF plus latent semantic analysis | Use TF-IDF followed by deterministic truncated SVD. It produces one genuine dense vector per product, remains offline, and is easier to inspect than a neural model. |
| Route combination | Fuse routes now; keep route outputs separate | Keep routes separate so M3 can measure each route's coverage. |

## Final decision

- Build one textual query by joining the values of current active claims in their stored order.
- Exclude indifferent claims and deduplicate repeated textual values.
- Represent every route result as an immutable `RetrievalHit` containing `parent_asin`, route-local `rank`, and route-local `score`.
- Index lexical text in separate catalog fields: title, categories, features, details, store, and description. Start with FTS5's default field weights.
- Build the facet index only from normalized category claims. Rank by the number of matched category tokens, then by stable product identifier.
- Build one field-labelled text document per product for dense retrieval. Fit TF-IDF with at most 20,000 features, reduce to at most 64 dimensions with truncated SVD and a fixed seed, normalize vectors, and use cosine similarity.
- Add `scikit-learn` as the one direct M3 dependency and lock it with the existing `uv` workflow.
- Request the same candidate depth from every route.

## Explicit non-goals

- No Agent integration, route fusion, RRF, candidate-budget truncation across routes, constraint filtering, final ranking, or target-aware tuning.
- No approximate nearest-neighbour index, neural embedding download, hosted model, multi-view vectors, learned sparse retrieval, token-level multi-vector retrieval, synonym expansion, or dynamic routing.
- No manual lexical field weights or facet weights before route evidence exists.

## Experiment boundary

After route correctness is verified, the user will run a fixed-session comparison of Recall@K, unique target contribution, candidate overlap, latency, and representative misses. Parameter values in this ADR are baselines, not permanent choices.

## Revisit trigger

Revisit a route only when the M3 comparison shows low recall, negligible unique contribution, excessive overlap, or unacceptable latency. A later experiment may replace LSA with a neural single-vector model or introduce route-specific depths.

## Authorization record

Selected under the user's explicit `Start M3` instruction on `2026-09-22` and the standing authority to choose simple implementation details while reserving comparison decisions for the user.
