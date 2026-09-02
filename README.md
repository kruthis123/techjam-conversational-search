# TechJam Conversational E-Commerce Search Challenge

Build an AI shopping agent that asks useful follow-up questions and recommends the customer's hidden target product within at most 10 turns.

## What You Receive

- A frozen catalog of 50,000 products from the `Clothing_Shoes_and_Jewelry` category of Amazon Reviews 2023.
- 200 labeled public sessions for local development.
- A weak BM25 starter agent and deterministic local evaluator.
- The Agent API contract and scoring rules.

The organizer keeps 800 additional sessions private for final evaluation.

## Task

For each session, your agent receives an anonymized preference profile and a short customer message. Raw user IDs, review text, timestamps, and purchase history are never disclosed. On every turn the agent may:

- ask a natural clarification question in `message` and identify one requested field in `ask_attribute`;
- return a ranked list of up to 10 catalog `parent_asin` values;
- do both in the same response.

The session ends when the target product appears in the scored Top 10 or after turn 10. Sessions cover Buying, Browsing, Intent Override, and Boundary behavior.

## Download the Catalog

Download `catalog.jsonl.gz` from the GitHub Release attached to this repository, then run:

```bash
gzip -dk catalog.jsonl.gz
mv catalog.jsonl data/catalog.jsonl
```

Verify the downloaded file using the published `SHA256SUMS` file.

## Set Up the Project

The project is tested on Python 3.12.14. Install the locked environment with
[`uv`](https://docs.astral.sh/uv/):

```bash
uv sync --python 3.12
```

`uv.lock` pins the complete dependency graph, including NumPy, PyTorch,
Transformers, and Sentence Transformers.

## Run the Agent

```bash
uv run python -m evaluator.local_evaluator
```

Edit `starter/agent.py` to implement your system. Do not edit the evaluator or public labels when reporting your local score.
The command writes per-session results and aggregate metrics to `results.json`.

The included weak BM25 starter scores Hit Rate@10 `0.125`, MRR `0.068034`, and
MTTC `9.81` on the released public set. See `docs/baseline_results.json`.

## Optional Dense Retrieval

Precompute the frozen catalog once with the pinned BGE encoder:

```bash
uv run python -m scripts.build_embeddings
```

This saves local model weights under `models/` and a checksum-validated float16
embedding matrix under `data/cache/embeddings/`. These generated artifacts are
ignored by Git and must be packaged or prepared separately for an offline run.
Runtime calls never download a model. To evaluate the experimental dense routes:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run python -m scripts.benchmark \
  --experiment dense_only --dense-variant dense_only

HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run python -m scripts.benchmark \
  --experiment hybrid_dense --dense-variant hybrid_dense
```

The selected submission default remains `dense_off` unless a dense configuration
beats the lexical pipeline on the development split. Missing or invalid dense
artifacts automatically fall back to lexical retrieval.

Task 11 also provides catalog-only field-aware indexes. They align separate
identity, attribute, and shopping-need product representations with matching
queries, then admit only non-contradictory dense-only candidates into the
semantic reranker head:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  uv run python -m scripts.build_fielded_embeddings

HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  uv run python -m scripts.benchmark --experiment task11_fielded \
  --dense-variant hybrid_dense_fielded
```

Use `hybrid_dense_fielded_profile` to add the supplied user profile as a
low-weight preference route. Profiles never act as hard filters and cannot
override the current conversation. These variants remain experimental until
their development and reserved-lockbox comparisons are recorded.

## Semantic Reranker

Prepare the selected local cross-encoder once:

```bash
uv run python -m scripts.prepare_reranker --model l4
```

The selected configuration reranks the first 60 Task 7 candidates with the
pinned MiniLM L4 model, batch size 32, and semantic rank weight 0.25. Model
weights are stored under `models/`, loaded with `local_files_only=True`, and are
never downloaded during `Agent.respond()`.

Run the selected pipeline with network access disabled:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  uv run python -m evaluator.local_evaluator
```

Use `--reranker-variant rerank_off` with `scripts.benchmark` to reproduce the
Task 7 control. Missing, invalid, or failed reranker artifacts automatically
preserve the original lexical ranking.

Post-lockbox research variants are also available for reproducible development
ablations. `minilm_l4_bounded` keeps the selected legacy context and prevents a
candidate from moving more than eight ranks during semantic reranking:

```bash
uv run python -m scripts.benchmark --experiment bounded_reranker \
  --reranker-variant minilm_l4_bounded
```

It improved the 160-session development TechnicalScore from `0.550224` to
`0.550972`, but remains experimental because the reserved lockbox had already
been consumed. The frozen submission default remains `minilm_l4_blended`.

## Adaptive Orchestration

The deterministic planner in `starter/orchestration.py` compiles the active
session state into a per-turn retrieval plan. It does not call an LLM. The
selected `adaptive_cutoff` variant preserves the Task 9 pipeline for normal
turns and skips dense retrieval and semantic reranking only when early Browsing
produces a saturated, weakly separated candidate pool. The agent still returns
the selected `always_10` recommendations and asks its normal clarification.

Run the frozen control, shadow mode, or selected adaptive variant with:

```bash
uv run python -m scripts.benchmark \
  --experiment task10_static --orchestration-variant static

uv run python -m scripts.benchmark \
  --experiment task10_shadow --orchestration-variant static_shadow

uv run python -m scripts.benchmark \
  --experiment task10_cutoff --orchestration-variant adaptive_cutoff
```

Benchmark artifacts include proposed and executed plan modes, decision reasons,
planner fallbacks, mean executed rerank depth, and reranker calls avoided. Any
planner failure uses the frozen static plan. The `adaptive_rerank`,
`adaptive_recovery`, and `adaptive_full` variants remain available for ablation
but are not selected defaults.

## Reliability and Performance

Every Agent response passes through a final local contract guard that removes
invalid or duplicate ASINs, enforces `top_k`, validates clarification attributes,
and emits zero-token local usage. Normal execution produces no guard warnings.
The deterministic fallback chain is:

```text
semantic reranker -> structured lexical -> single BM25
                  -> category/global popularity -> valid empty response
```

Run the frozen path with networking disabled:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  uv run python -m scripts.benchmark \
  --experiment offline_readiness --split development
```

The Task 12 forced-offline development run reproduced TechnicalScore `0.550224`
with zero exceptions, warnings, or fallbacks over 948 turns. It measured an
8.27-second startup, 347ms mean and 477ms p95 turn latency, 1.76GB peak process
memory, 337.9-second wall time, and 131.5MB of required catalog/model artifacts.
The selected path makes no external API calls and has zero external inference
cost. The reserved lockbox was not rerun.

## Build and Verify the Submission

Create the deterministic submission archive:

```bash
uv run python -m scripts.package_submission
```

Verify its file manifest, catalog checksum, response contract, bundled model,
and forced-offline execution from a temporary extracted directory:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  uv run python -m scripts.check_submission
```

The final bundle is `dist/techjam-shopping-agent.zip`. It exports
`agent:Agent`, includes only the selected MiniLM-L4 model and required source,
and intentionally excludes the catalog, development labels, evaluator,
experiments, rejected models, caches, and secrets. The final archive is
70,284,156 bytes with SHA256
`65ebdd0df2ea2f692fe882d137ea05fc8fc58da367a1c8eea0bdad7aac314076`.
Building it twice produces the same checksum.

Run the label-free six-turn demo from the repository with:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  TECHJAM_CATALOG_PATH="$PWD/data/catalog.jsonl" \
  uv run python submission/demo.py
```

The archive contains its own setup guide, technical report, model/cost
disclosure, limitations, file hashes, and the same demo.

## Agent Interface

```python
class Agent:
    def reset(self, session_id: str, user_profile: dict) -> None:
        ...

    def respond(self, session_id: str, user_message: str, turn: int, top_k: int) -> dict:
        return {
            "message": "Do you have a material preference?",
            "ask_attribute": "material",
            "recommendations": [
                {"parent_asin": "B000..."},
                {"parent_asin": "B001..."}
            ],
            "usage": {"prompt_tokens": 120, "completion_tokens": 30}
        }
```

`ask_attribute` is one of `category`, `material`, `color`, `size`, `style`, `brand`, `budget`, `feature`, `use_case`, `other`, or `null`. See `docs/agent_api_contract.json`.

## Technical Metrics

- **Hit Rate@10:** fraction of sessions that find the target within 10 turns.
- **MRR:** mean reciprocal rank of the target; a miss contributes zero.
- **MTTC:** mean first-hit turn; a miss is assigned turn 11.
- **Reported token usage:** prompt and completion tokens returned by the team's model client.

```text
TechnicalScore = 0.50 × HitRate@10 + 0.30 × MRR + 0.20 × Efficiency
Efficiency = clip((11 - MTTC) / 10, 0, 1)
```

`TechnicalScore` is an objective input to the `Technical Execution` assessment. It is not a separate judging criterion and does not represent the entire `Technical Execution` score.

Only exact `parent_asin` equality produces a hit. Core metrics are also reported by scenario.

## Model Choice and Cost

Teams may use any legally accessible LLM API or local model. Teams manage their own credentials and must never commit API keys. Model choice, estimated cost, token usage, and latency must be disclosed. Token usage is a feasibility metric, not part of the core technical score. The organizer does not provide or reimburse model API credits; teams are responsible for any costs incurred through optional external services.

## Files

```text
data/public_set.jsonl             200 labeled development sessions
docs/competition_specification.md participant rules and evaluation protocol
docs/agent_api_contract.json      machine-readable Agent contract
docs/evaluation_config.json       scoring configuration
docs/baseline_results.json        reproducible weak-starter reference score
starter/agent.py                  editable weak starter
evaluator/local_evaluator.py      public-set simulator and scorer
```

## Judging and Submission Policy

- Participant submission requirements: `docs/submission_rules.md`
- Organizer-only final judging controls: `organizer/JUDGING_RUNBOOK.md`
- Organizer private release checklist: `organizer/private_release_checklist.md`
- Judging day operations SOP: `organizer/JUDGING_DAY_SOP.md`

## Data Source

The catalog and sessions are derived from Amazon Reviews 2023 by McAuley Lab, UCSD. See `DATA_ATTRIBUTION.md` before using or redistributing the data.
Sessions are sampled deterministically from the official Clothing 5-core leave-last-out split and joined to the frozen catalog.
