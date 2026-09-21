# SDR-004: Candidate retrieval

- Status: `Synthesized`
- Author: `User`
- Date: `2026-09-16`
- System-design area: `SD-04`
- Related learning cards: `LC-04`, `LC-12`, `LC-13`
- Case-study references: `docs/competition_specification.md`, `docs/evaluation_config.json`

## System question

How should the agent generate a high-recall candidate pool from the current active intent and the catalog representations without confusing retrieval evidence with factual constraint satisfaction or final ranking?

## Why this capability matters

Retrieval narrows a 50,000-product catalog to a candidate pool that later capabilities can inspect and rank. A relevant product omitted here cannot be recovered by constraint checking or reranking. Conversely, retrieval can tolerate some false positives because later stages can reject contradictions and improve ordering.

The case study scores only the first ten valid unique product identifiers, but retrieval should normally produce a broader internal pool. `SD-05` will decide constraint-aware eligibility and `SD-06` will decide final ordering.

## Information available

- the current active intent from `SD-03`, including product need, requirements, preferences, exclusions, indifference, uncertainty, and provenance;
- raw user wording and grounded turn evidence when useful for semantic or lexical matching;
- raw catalog fields, normalized facets, lexical representations, and dense embeddings selected in `SD-01`;
- optional inferred intent or product views, which may improve recall but cannot establish hard facts;
- the required output depth and operational limits.

The hidden target, private intent card, and evaluator state are unavailable.

## Useful representations

Potential query-side representations include:

- raw or field-labelled user text;
- normalized product category and attribute-value terms;
- separate query views for product identity, use case, features, and descriptive preferences;
- lexical term weights or expanded terms;
- one dense query embedding or several view-specific embeddings;
- hard requirements, exclusions, and uncertain claims supplied as metadata rather than collapsed into one similarity query.

Potential retrieval output includes product identity, retrieval route, route-local rank and score, matched query view or terms, and links to supporting catalog representations. These are candidate-generation signals, not final relevance judgments.

## Solution families to learn

- fielded lexical retrieval, including exact lookup and BM25-style matching;
- faceted or structured retrieval over normalized catalog attributes;
- dense vector retrieval using one query and product vector;
- multi-view dense retrieval using several intent and product views;
- learned sparse retrieval;
- token-level multi-vector or late-interaction retrieval;
- taxonomy- or graph-assisted expansion and traversal;
- hybrid parallel retrieval followed by candidate union, score fusion, or route-aware downstream ranking;
- adaptive routing, where the active intent determines which retrieval routes and depths to use.

## What I need to research

- Concepts and vocabulary: candidate generation, recall, precision, query formulation, field weighting, exact lookup, inverted index, BM25, dense retrieval, approximate nearest neighbours, learned sparse retrieval, late interaction, hybrid retrieval, rank fusion, query expansion, routing, and retrieval depth.
- Algorithms or system patterns: BM25-style retrieval, facet lookup, dense nearest-neighbour search, reciprocal-rank fusion, weighted score fusion, multi-query or multi-view retrieval, and route selection.
- Questions the research must answer:
  - Which intent information belongs in a retrieval query, and which should remain available for later constraint checking?
  - Which retrieval families cover exact attributes, catalog wording mismatch, use cases, and broad browsing intent?
  - Should routes run in parallel for every turn or be selected according to intent?
  - How should route outputs be combined when their scores are not comparable?
  - How large must the candidate pool be before later filtering and ranking?
  - Which recall failures would justify learned sparse, multi-vector, taxonomy, or graph retrieval?

## Comparison criteria

- target Recall@K and recall by query slice;
- marginal unique relevant candidates contributed by each route;
- false-positive composition rather than precision alone;
- robustness to exact attributes, aliases, semantic use cases, and mixed intents;
- sensitivity to missing or inferred metadata;
- index size, preprocessing cost, query latency, memory, and operational reliability;
- explainability of why a candidate entered the pool;
- stability across fixed public and held-out sessions.

## Worked example or thought experiment

Active intent: "I need an everyday bag for a rainy commute. Nylon only, fits a 15-inch laptop, under $80."

- A lexical route may retrieve products containing `nylon`, `15-inch`, `laptop`, or `commuter`.
- A facet route may retrieve products whose normalized material, laptop-size, category, and price values align with the request.
- A dense route may retrieve products described as weather-ready work or travel bags even when they do not use the phrase `rainy commute`.
- A multi-view route may search the product type, use case, and requested features separately so one broad use-case phrase does not dilute exact product information.

At this stage, a candidate may enter through weak semantic similarity or partial matching. Whether it contradicts `nylon only`, genuinely supports the laptop requirement, or should appear in the final top ten belongs to later capabilities.

## Learning experiment

Begin with a paper route-coverage matrix over fixed query slices: exact product or model, category plus attributes, semantic use case, broad browsing request, and mixed hard and soft constraints. Record which route should retrieve each target, expected unique contribution, and likely false positives.

If conceptual comparison does not distinguish the routes, run an offline benchmark on identical sessions and candidate depths. Compare route-level and union Recall@K, unique target contribution, latency, and failure slices. Do not compare final ranking quality until the candidate sets are fixed.

## My synthesis

### User's initial direction

1. Begin with BM25 or other lexical matching, dense retrieval, and facet retrieval.
2. Defer multi-view dense retrieval, learned sparse retrieval, and token-level multi-vector retrieval.
3. Begin with one unified intent query per retrieval family. Introduce decomposed or multi-view queries only if evaluation shows that important intent aspects are being diluted or missed.
4. Retrieval does not own final hard-requirement enforcement. It may use requirements to retrieve likely matches, but post-retrieval elimination, contradiction handling, missing-attribute treatment, and any relaxation policy are deferred to `SD-05`.
5. Merge route outputs using rank fusion, then reduce the fused result to a bounded candidate pool before passing it to `SD-05`.
6. Begin with reciprocal-rank fusion (`RRF`) so route-local ranks can be combined without treating lexical, dense, and facet scores as directly comparable.
7. Order facet-route results initially by the number of matched facets. Test weighting matched facets according to user stance, such as giving requirements more influence than preferences, rather than assuming that weighting improves retrieval.
8. Select the fused candidate-pool cutoff experimentally instead of deriving it from the evaluator's final top-ten output size.
9. Do not add a separate exact-match route initially. BM25 or the selected fielded lexical route is the sole lexical candidate generator in the baseline.
10. Run every baseline route on every turn. Reconsider adaptive route selection only after measuring each route's unique candidate contribution, overlap or redundancy, and operational cost.
11. Retrieve the same number of candidates from every route initially. Consider unequal route depths only after route-level recall, unique contribution, noise, and latency have been compared on identical sessions.

### Facilitator refinement

- BM25 is itself a lexical retrieval method. The baseline should later clarify whether "lexical" means exact or fielded term matching in addition to BM25, rather than treating BM25 and lexical retrieval as unrelated families.
- A unified query is represented appropriately for each route: textual terms for lexical retrieval, normalized attribute-value input for facet retrieval, and one embedding for dense retrieval. It does not require forcing every route to consume an identical query format.
- Facet retrieval may add products with confirmed attribute matches to the candidate pool. It must not silently turn missing facet values into contradictions or globally eliminate candidates produced by other routes; that policy belongs to `SD-05`.
- Pre-validation fusion is a candidate-budget decision, not proof that highly fused products satisfy the user's requirements. The fused order and contributing-route evidence must remain available to downstream capabilities.
- Truncating after fusion can remove a target found strongly by only one route. Evaluate target recall before and after the fusion cutoff, including unique contributions from each route. Revisit the decision and omit pre-validation fusion or truncation if its recall loss is not justified by downstream cost or latency reduction.
- Facet-route stance weighting affects only route-local retrieval priority. It does not validate requirements, eliminate contradictions, or replace `SD-05`.
- Compare unweighted facet-match count against stance-weighted facet ordering on identical sessions. Retain weighting only if it improves post-cutoff recall without disproportionately suppressing products whose metadata is incomplete.

Further retrieval decisions remain open around the experimental thresholds and failure evidence that would change the unified-query, fusion, cutoff, or deferred-family choices.

### User's revisit triggers

- Introduce multi-view dense retrieval when the single dense vector has lower recall because important terms or intent aspects lose their meaning when compressed into one representation.
- Treat low unique candidate contribution as the first signal that an always-on route may be unnecessary. Examine whether its candidates contribute to final recommendations, then consider overlap and operating cost before introducing dynamic routing.
- Revisit pre-validation RRF truncation when the target exists in the full unified candidate pool but is absent after the RRF cutoff.

### Facilitator refinement of the triggers

- Diagnose a single-vector miss by checking whether separate intent aspects can retrieve the target; otherwise the problem may be the embedding model, product representation, or catalog evidence rather than query-view dilution.
- Final-list survival alone is not a reliable measure of route usefulness because constraint or ranking errors can suppress good candidates. Measure unique target recovery, counterfactual end-to-end impact when the route is removed, overlap by query slice, latency, and resource cost.
- A fusion-induced target loss should first identify whether the remedy is a larger cutoff, different RRF settings, a per-route candidate reservation, or removal of pre-validation truncation. Compare recall loss against the actual validation cost saved.

## Connections to the rest of the agent

- Information required from upstream capabilities: catalog representations from `SD-01`, current active intent from `SD-03`, and grounded claim provenance from `SD-02`.
- Information supplied to downstream capabilities: a candidate pool with product identity, retrieval-route evidence, and route-local scores or ranks.
- New questions created for later areas: how contradictions and unknowns affect candidate eligibility, how route evidence is normalized for ranking, and how candidate coverage can inform clarification.

## Architecture critic feedback

Awaiting user synthesis.

## Revisit conditions

Revisit when constraint checking, ranking, dialogue policy, or evaluation reveals systematic candidate omissions, unacceptable latency, or redundant retrieval routes.
