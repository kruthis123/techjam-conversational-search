# Technical Report

## Method

The agent keeps typed per-session state and separates Buying, Browsing, Intent
Override, and Boundary behavior. A deterministic understanding layer extracts
catalog-grounded category and attribute slots. New turns accumulate compatible
slots; explicit overrides invalidate only superseded constraints and allow
previously shown products to be reconsidered.

Retrieval combines category, fielded BM25, broad lexical, and structured
constraint routes. Reciprocal-rank fusion creates a 200-item candidate pool.
The selected local `cross-encoder/ms-marco-MiniLM-L4-v2` model semantically
reranks the first 60 candidates using retrieval weight 1.0 and semantic weight
0.25. An adaptive planner skips semantic reranking for early, overloaded,
weakly separated browsing pools. The agent still asks a targeted clarification
and returns ten recommendations on every normal turn.

No LLM or external API is called. Intent parsing, slot extraction, question
selection, memory updates, retrieval routing, and orchestration are deterministic.

## Reproducible results

| Run | Sessions | Hit@10 | MRR | MTTC | TechnicalScore |
|---|---:|---:|---:|---:|---:|
| Frozen development | 160 | 0.700000 | 0.349080 | 6.225000 | 0.550224 |
| One-time reserved lockbox | 40 | 0.675000 | 0.298115 | 6.050000 | 0.525934 |

The lockbox was evaluated exactly once and was not used to change the frozen
configuration. A later development-only bounded-reranking result remains
experimental and is not included in this bundle.

## Efficiency and cost disclosure

The forced-offline 160-session run completed 948 turns with zero unhandled
exceptions, contract warnings, fallbacks, tokens, or external calls. Measured on
the development machine:

- Startup: 8.27 seconds
- Mean turn latency: 347 ms
- P95 turn latency: 477 ms
- Peak process memory: 1.76 GB
- Catalog plus selected model artifacts: 131.5 MB
- Prompt/completion tokens: 0 / 0
- External inference cost: $0

The bundle contains the 73 MB Apache-2.0 MiniLM-L4 model. The read-only 50,000
product catalog is organizer-provided and intentionally excluded.

## Reliability

Every response passes through a final contract guard. The fallback chain is:

```text
semantic reranker -> structured lexical -> single BM25
                  -> category/global popularity -> valid empty response
```

Missing or invalid model assets therefore reduce ranking quality but do not
break the Agent API.

## Limitations

- Slot extraction is catalog-grounded and rule-based, so highly indirect or
  novel phrasing may be under-parsed.
- Dense retrieval was tested but did not improve the untouched evaluation gate;
  it is excluded to reduce latency, memory, and overfitting risk.
- The cross-encoder is CPU-compatible but dominates per-turn latency.
- Session memory is process-local and intentionally not shared across users.
- Product recommendations contain IDs only; natural-language explanations are
  outside the scored contract and three-day scope.
