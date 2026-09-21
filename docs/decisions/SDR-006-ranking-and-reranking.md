# SDR-006: Ranking and reranking

- Status: `Synthesized`
- Author: `User`
- Date: `2026-09-17`
- System-design area: `SD-06`
- Related learning cards: `LC-06`, `LC-12`
- Case-study references: `docs/competition_specification.md`, `docs/evaluation_config.json`

## System question

How should the agent order confirmed and provisional candidates using relevance, preference, evidence quality, popularity, and retrieval signals without allowing weak signals to override hard requirements or incomparable score scales to distort the result?

## Why this capability matters

Retrieval determines whether the target enters the candidate pool, and `SD-05` removes confirmed contradictions. Ranking determines whether a retained target appears in the scored top ten and how high it appears. The evaluator rewards early target rank through reciprocal rank and ends most sessions after a hit, so ordering quality affects both rank and conversation length.

Ranking must preserve the semantic decisions already made upstream. It may order confirmed and provisional candidates, but it cannot restore an ineligible candidate merely because the product is popular or semantically similar.

## Information available

- confirmed or provisional eligibility and per-constraint assessments from `SD-05`;
- active hard requirements, soft preferences, exclusions, indifference, and inferred intent;
- BM25, dense, facet, and RRF route evidence from `SD-04`;
- raw and normalized catalog evidence with provenance from `SD-01`;
- product popularity signals such as average rating and rating count;
- optional historical-profile signals, whose appropriate use is deferred to `SD-08`;
- scenario, turn, latency, and token constraints where available.

The hidden target and private intent card remain unavailable. Retrieval scores from different routes are not directly comparable without calibration or rank-based treatment.

## Useful representations

A ranking record for each retained candidate may include:

- eligibility tier and number or importance of confirmed, inferred, unknown, and ambiguous assessments;
- lexical, dense, facet, and fused retrieval ranks or normalized scores;
- exact product-category and attribute evidence;
- soft-preference matches and conflicts;
- catalog-evidence provenance and missingness;
- popularity or quality priors;
- profile-prior signals when later authorized;
- final ranking score, ordering explanation, and feature contribution or evidence trace.

These are ranking signals, not replacements for raw catalog facts or active intent.

## Solution families to learn

- lexicographic or tier-first ranking, where eligibility and higher-priority evidence dominate lower-priority signals;
- hand-built rules and weighted scoring over normalized features;
- rank aggregation using route-local ranks;
- learning-to-rank using pointwise, pairwise, or listwise objectives;
- cross-encoder or semantic reranking over query-product pairs;
- LLM-based comparison or reranking;
- cascaded ranking, where cheap features reduce the pool before an expensive reranker;
- diversity-aware or intent-coverage reranking for browsing scenarios.

## What I need to research

- Concepts and vocabulary: relevance, feature, prior, calibration, normalization, monotonicity, lexicographic ordering, pointwise, pairwise, listwise, cross-encoder, reranker, diversity, novelty, exposure, and tie-breaking.
- Algorithms or system patterns: weighted scoring, rank aggregation, learning-to-rank, pairwise comparison, maximal marginal relevance, cascaded reranking, and calibrated feature combination.
- Questions the research must answer:
  - Must every confirmed candidate rank above every provisional candidate, or should uncertainty be a penalty rather than a strict tier?
  - Which signals represent current-request relevance, soft preference, product quality, historical prior, and retrieval confidence?
  - Which signals may dominate others, and which must remain bounded?
  - How can incompatible scores be normalized or avoided?
  - When does a learned or semantic reranker add value beyond transparent rules?
  - Should Buying and Browsing scenarios use different ranking objectives?
  - How should diversity affect a top-ten list when reciprocal rank rewards one hidden target?

## Comparison criteria

- MRR and target rank on fixed candidate sets;
- HitRate@10 after ranking, separated from retrieval recall;
- pairwise ordering accuracy for known preference and evidence relationships;
- target movement by ranking stage and failure slice;
- contradiction leakage, which should remain zero after `SD-05`;
- robustness by scenario, category, turn, and metadata completeness;
- calibration, explainability, latency, token cost, and operational stability;
- public-development versus held-out behavior and sensitivity to tuning.

## Worked example or thought experiment

All candidates have survived `SD-05`:

| Candidate | Eligibility | Request relevance | Soft preference | Catalog evidence | Popularity |
|---|---|---|---|---|---|
| A | confirmed | strong | misses preferred blue | complete | moderate |
| C | provisional: material unknown | very strong | matches blue | incomplete | high |
| E | provisional: material inferred | strong | matches blue | inferred support | moderate |
| F | confirmed | moderate | matches blue | complete | very high |

The exercise is to decide whether eligibility is a strict tier or a bounded penalty, how much a soft preference may change order, and whether popularity may break ties or materially drive ranking.

## Learning experiment

Hold candidate sets fixed and compare ranking policies on identical sessions:

1. retrieval-fusion order only;
2. tier-first rule ranking;
3. normalized weighted scoring;
4. an additional semantic or learned reranker only if the simpler policies expose a named error slice.

Measure MRR, HitRate@10, pairwise decision accuracy, target movement, latency, and results by scenario and metadata-completeness slice. Change one ranking factor at a time and preserve a final holdout to reduce repeated public-set tuning.

## My synthesis

### User's initial direction

1. Use a bounded uncertainty penalty rather than forcing every confirmed candidate above every provisional candidate. A sufficiently relevant provisional candidate may therefore outrank a weaker confirmed candidate.
2. Prioritize ranking-signal groups in this order:
   1. current-request relevance;
   2. retrieval evidence;
   3. soft-preference matches;
   4. product popularity.
3. Begin with normalized weighted scoring.
4. Consider a more complex reranker when the target reaches the fixed reranking candidate set but weighted scoring produces inconsistent top-result or top-ten failures, and reasonable weight adjustment cannot fix the error slice without harming other cases.
5. Start with a strict hierarchy between the selected signal groups rather than allowing lower-priority groups to compensate for a meaningful difference in a higher-priority group. Reconsider this only if controlled experiments show systematic ranking errors where lower-priority evidence should dominate.
6. Accumulate uncertainty penalties across uncertain hard requirements, subject to a bounded total penalty.
7. Normalize each signal according to its own meaning and distribution rather than forcing every feature through one common normalization method.
8. Use exact score differences for the initial strict hierarchy; do not introduce tolerance bands initially.
9. Use product popularity only as the final tie-breaker rather than as a normal ranking group capable of overcoming relevance, retrieval evidence, or soft preferences.
10. Use the same ranking policy for Buying and Browsing initially. Introduce scenario-specific or diversity-aware ranking only when slice-level experiments show a systematic need.
11. Keep current-request relevance features independent from retrieval-route evidence: direct intent-to-product comparisons belong to relevance, while BM25, dense, facet, and RRF ranks belong only to the retrieval-evidence group. Do not count the same signal in both groups.
12. Select within-group weights, per-uncertainty penalties, and the total uncertainty cap experimentally from the beginning rather than starting from manually chosen production values.
13. Replace exact hierarchy with tolerance bands when small score perturbations repeatedly change target ordering or near-equal relevance candidates are consistently ordered incorrectly.

### Facilitator refinement

- The uncertainty penalty applies only to candidates retained by `SD-05`; a confirmed hard contradiction remains ineligible and cannot be rescued by ranking.
- Preserve the distinction selected in `SD-05`: inferred matching evidence is stronger than completely unknown evidence, but both remain provisional and below confirmed evidence.
- A few target misses do not by themselves justify a complex reranker. Diagnose whether the failure comes from missing features, unsuitable normalization, linear weighting that cannot represent interactions, scenario-dependent objectives, or noisy labels.
- Compare any complex reranker against weighted scoring on identical fixed candidate sets and held-out slices. Adopt it only when it improves the named ranking failure without unacceptable regressions, latency, cost, or loss of reproducibility.
- Combine strict group priority with normalized weighted scoring by using lexicographic comparison between groups and weighted scoring within a group. Otherwise an unconstrained weighted sum would contradict the selected strict hierarchy.
- Test both per-uncertainty increments and the total cap. Without a cap, missing metadata across several constraints could suppress a highly relevant target without bound.
- Exact comparison can make very small numerical differences dominate every lower-priority group. Revisit it if ranking changes under insignificant score perturbations or if near-equal relevance candidates are consistently ordered poorly.
- Because popularity is a final tie-breaker under exact comparison, it may rarely affect results. This is consistent with the selected priority but should be verified rather than assuming popularity contributes materially.
- Compare Buying and Browsing slices separately even while using one policy. Aggregate improvement can hide a broad-query coverage or diversity regression.
- Parameter experiments must use identical fixed candidate sets, product- or intent-separated tuning and holdout sessions, and unchanged feature definitions. Report MRR and HitRate@10 plus scenario and metadata-completeness slices so optimization does not silently trade one failure class for another.

The exact parameter values remain intentionally open until the ranking experiment is run. A more complex reranker remains conditional on the recorded fixed-candidate failure trigger.

## Connections to the rest of the agent

- Information required from upstream capabilities: active intent from `SD-03`, catalog evidence from `SD-01`, retrieval-route evidence from `SD-04`, and eligibility assessments from `SD-05`.
- Information supplied to downstream capabilities: an ordered candidate list with ranking evidence and uncertainty information for recommendation and dialogue decisions.
- New questions created for later areas: whether to ask before presenting provisional products, how historical profile signals enter ranking, when orchestration switches rerankers, and how explanations expose ranking evidence.

## Architecture critic feedback

Awaiting user synthesis.

## Revisit conditions

Revisit when fixed-candidate evaluation shows targets being demoted by soft signals, provisional handling causing false suppression, scenario-specific regressions, unstable score calibration, or unacceptable reranking cost.
