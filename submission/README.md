# TechJam Shopping Agent Submission

This bundle exports `agent.Agent` and runs entirely offline during inference.
It uses deterministic intent/slot understanding, multi-route structured lexical
retrieval, adaptive cutoff orchestration, and a local MiniLM-L4 cross-encoder.

## Requirements

- Python 3.12 (tested with 3.12.14)
- The organizer-provided `catalog.jsonl`, SHA256
  `da979b05a68af864cb0dcf9ee6a81c010c7e66a57978ad286c7a2e005fc69a67`
- Approximately 2 GB available RAM; CPU execution is supported
- No network access or credentials are required at inference time

Install dependencies in a clean environment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Official entry point

Configure the harness to import:

```text
agent:Agent
```

The harness may pass the catalog path to `Agent(catalog_path)`. If it constructs
`Agent()` without arguments, set `TECHJAM_CATALOG_PATH` to the catalog's absolute
path. The bundled model path is resolved automatically.

From the organizer kit, the equivalent evaluator command is:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TECHJAM_CATALOG_PATH=/absolute/path/to/data/catalog.jsonl python -m evaluator.local_evaluator
```

## Local smoke test and demo

Run a six-turn conversation without labels or external services:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TECHJAM_CATALOG_PATH=/absolute/path/to/data/catalog.jsonl python demo.py
```

The demonstration covers vague browsing, a no-preference boundary, information
accumulation, an explicit intent override, stale-slot invalidation, and final
convergence.

## Frozen configuration

- Recommendation policy: `always_10`
- Retrieval: `multi_route_structured`
- Dense route: `dense_off`
- Reranker: `minilm_l4_blended`, depth 60, semantic weight 0.25
- Orchestration: `adaptive_cutoff`

See `REPORT.md` for evaluation results, latency, memory, model disclosure,
fallback behavior, and limitations. `MANIFEST.json` records all bundled file
hashes and the exact frozen configuration.
