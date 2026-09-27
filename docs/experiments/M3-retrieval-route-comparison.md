# M3 experiment: Compare retrieval-route coverage

## Decision owner

The user completed the tuning interpretation and selected depth 100 with BM25,
facet, and SVD-256 as the provisional route set. Permanent retention remains a
later user-owned decision after dialogue integration.

## What was implemented

- One shared query joins current non-indifferent intent values.
- Lexical retrieval uses an in-memory SQLite FTS5 BM25 index over six catalog text fields.
- Facet retrieval uses normalized category tokens and ranks by distinct token matches.
- SVD-256 retrieval reduces field-labelled TF-IDF documents to at most 256 latent dimensions and ranks normalized vectors by cosine similarity.
- Every route receives the same query and requested depth and returns product ID, route-local rank, and route-local score.
- The comparison runner reports route and union Recall@K, unique target contribution, pairwise overlap, timing, scenario/difficulty counts, and five misses per route.

The earlier raw-TF-IDF route and dense-vectorization comparison remain available
for reproducing those diagnostic experiments. `svd_256` is an inspectable LSA
baseline, not a pretrained semantic embedding.

No route fusion, hard-constraint filtering, final reranking, Agent integration, neural embedding, or multi-turn retrieval is implemented.

## Why this is a first-turn experiment

Dialogue policy does not exist yet, so this experiment uses only the first official simulator message. It evaluates candidate coverage, not end-to-end agent quality.

The public file omits hidden intent cards. The official evaluator therefore uses the public target inside its simulator-materialization boundary to reconstruct that first message. Retrieval receives only the message-derived query; it never receives the target ID or target product as a search hint.

## Fixed split

- Tuning: 160 sessions — 64 Buying, 64 Browsing, 24 Intent Override, 8 Boundary.
- Holdout: 40 sessions — 16 Buying, 16 Browsing, 6 Intent Override, 2 Boundary.
- Selection is deterministic within each scenario and the sets do not overlap.

Do not run the holdout before dialogue integration. This deferral is
unconditional: the completed tuning choice does not authorize a first-turn
holdout run. A later approved task must explicitly reopen the experiment with
multi-turn queries.

## Historical tuning result

The route/depth selection step is complete. At depth 100, the user selected
BM25, facet, and SVD-256 from the recorded tuning evidence. TASK-017 only wires
that decision into the runner; its verification does not rerun tuning or
holdout.

## How the tuning evidence was read

At K=100, compare:

1. `route_recall_at_k`: how often each route contains the target.
2. `union_recall_at_k`: coverage available if later fusion preserves every route's candidates.
3. `unique_target_contribution`: targets found by exactly one route. This is the clearest reason to retain an otherwise weaker route.
4. `mean_pairwise_jaccard_overlap`: low overlap means routes bring different candidates; high overlap plus no unique targets suggests redundancy.
5. Build, mean-search, and p95-search time: the cost of the coverage gained.
6. Scenario and difficulty counts: whether aggregate performance hides a weak slice.
7. `queries_by_sample_id`: inspect the one message-derived query shared by all three routes for every evaluated session.
8. `representative_misses`: inspect each miss's `query` beside its retrieved product IDs to interpret whether failures look lexical, category-based, or caused by latent-vector matching.

Do not compare route-local raw scores; BM25, facet counts, and cosine similarity
are on different scales.

These interpretation steps are retained as historical context, not instructions
to choose routes again. The next retrieval comparison belongs after dialogue
integration, when stronger later-turn queries exist.
