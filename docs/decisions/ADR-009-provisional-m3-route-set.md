# ADR-009: Provisional M3 retrieval route set

- Status: `Accepted under M3 authorization`
- Date: `2026-09-27`
- Supersedes: `ADR-008` for the active third route

## Context

At tuning depth 100, BM25 recall was 0.5125, facet recall was 0.4125, and raw
TF-IDF recall was 0.35. Raw TF-IDF overlapped BM25 by 0.4763 and added only two
unique targets, while facet retrieval added fourteen. The user concluded that
the remaining misses mostly reflected under-specified first-turn queries and
many similarly suitable catalog products.

The vectorization diagnostic showed SVD-256 recall of 0.2375, above SVD-64 at
0.1875. SVD-256 has not yet been compared directly against the final BM25 and
facet pair, so its selection is provisional rather than a permanent route
decision.

## Decision

- Use BM25, facet, and SVD-256 as the provisional retrieval routes.
- Remove raw TF-IDF from the active three-route comparison because its marginal
  target contribution does not justify a second similar lexical route.
- Preserve raw TF-IDF and all M3 experiment code and evidence for learning and
  reproducibility.
- Keep the route name `svd_256`; do not describe it as a pretrained semantic
  embedding.
- Re-evaluate all routes after dialogue integration supplies stronger later-turn
  queries. That later experiment owns permanent route retention.
- Close M3 using tuning evidence. The user explicitly defers the M3 holdout
  because first-turn-only evaluation is not representative of the intended
  conversational retrieval behavior.

## Consequences

- The baseline retains one strong lexical route, one structured category route,
  and one latent dense route.
- SVD-256 remains an intentionally weak, inspectable baseline rather than a
  claim that neural dense retrieval has been evaluated.

## Approval record

Accepted by the user's explicit instruction to use BM25, facet, and SVD-256
provisionally and mark M3 complete on `2026-09-27`.
