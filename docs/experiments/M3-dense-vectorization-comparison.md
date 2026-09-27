# M3 experiment: Compare dense vectorizations

## Decision owner

The user runs and interprets this tuning experiment. Codex has verified the
runner but has not run the full-catalog comparison, used the holdout, or selected
a winning vectorization.

## Decision question

Does raw TF-IDF cosine or a 256-dimensional TF-IDF/SVD representation improve
candidate coverage enough to replace the current 64-dimensional TF-IDF/SVD
baseline?

## Controlled comparison

All three variants use:

- the same field-labelled product documents as the current dense route;
- one shared TF-IDF vocabulary capped at 20,000 features;
- the same product order and first-turn queries;
- cosine similarity with deterministic product-ID tie-breaking; and
- the fixed 160-session tuning split from the M3 route comparison.

Only the vectorization changes: raw TF-IDF, SVD capped at 64 dimensions, or SVD
capped at 256 dimensions. Target product labels are not supplied to indexing or
retrieval; they are used only when completed candidate lists are summarized.

## Run both depths once

From the repository root:

```bash
unset VIRTUAL_ENV && uv run --python 3.12 python -m experiments.m3_compare_dense_variants --depth 50 100 --output /tmp/m3-dense-vectorizations.json
```

The indexes are built once, every query is retrieved once at the largest depth,
and the same candidate lists are truncated to summarize both depths. The command
may take several minutes on the full catalog and also prints the JSON result.

Do not run this experiment on the holdout. The command intentionally selects the
tuning split without offering a holdout option.

## How to read the result

For each entry under `depths`, compare:

1. `variant_recall_at_k` and `union_recall_at_k` for target coverage.
2. `unique_target_contribution` for targets found by only one vectorization.
3. `mean_pairwise_jaccard_overlap` for candidate-list similarity.
4. Build, mean-search, and p95-search timing for the cost of each alternative.
5. `scenario_recall_counts` and `difficulty_recall_counts` for hidden aggregate
   regressions.
6. Up to five `representative_misses` per variant and for the union, with the
   first-turn query and retrieved product IDs available for inspection.

Each variant's search timing measures its own projection (when applicable),
cosine scoring, and ranking. The one shared TF-IDF query transformation is
consistently excluded, so compare the reported values as variant-specific work
rather than complete standalone query latency. Build timing includes the shared
TF-IDF fit for each SVD variant plus that variant's reduction.

## Decision to report

Reply with:

```text
Depth: 50 / 100 / test another value
Dense vectorization: raw TF-IDF / SVD 64 / SVD 256 / defer
Most important recall evidence: ...
Unique contribution or overlap evidence: ...
Timing evidence: ...
Miss pattern worth investigating: ...
Reasoning: ...
```

Choosing a variant remains a user-owned M3 experiment decision. This comparison
does not modify `starter/dense_retrieval.py` or the active retrieval route.
