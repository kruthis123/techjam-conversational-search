# Conversational Shopping Agent — Living Implementation Plan

Last updated: 2026-08-30

This is the canonical, dynamically maintained task list for the hackathon MVP. Update this file after completing a task, changing an architectural decision, or recording an experiment result.

## How to use this plan

- `[ ]` means pending, `[x]` means completed.
- Each task has a status, dependencies, outcome, required knowledge, implementation steps, alternatives, and a completion gate.
- Do not start a model-heavy task until its deterministic dependencies pass their completion gates.
- Ask Codex things such as "mark Task 0 complete", "add this result to Task 6", or "revise the dense retrieval decision" to update this file during the chat.
- Never edit the official evaluator or public labels to improve a reported score.

## Current status

| Task | Status | Day | Outcome |
|---|---|---:|---|
| 0. Understand evaluation | Completed | 1 | Correct mental model of contract and scoring |
| 1. Reproduce baseline | Completed | 1 | Frozen baseline result |
| 2. Experiment runner | Completed | 1 | Repeatable diagnostics and ablations |
| 3. Product representation | Completed | 1 | Normalized read-only product store |
| 4. Session state machine | Completed | 1 | Accumulation, override, and boundary state |
| 5. Parser and router | Completed | 1 | Buying/Browsing routing and event detection |
| 6. Clarification and recommendation policy | Completed | 1 | Confidence-aware dynamic truncation |
| 7. Multi-route lexical retrieval | Completed | 1–2 | High-recall lexical candidate pool |
| 8. Dense retrieval | Completed (`dense_off` selected) | 2 | Tested semantic candidate route with safe lexical fallback |
| 9. Semantic reranking | Completed (MiniLM L4 selected) | 2 | Higher Top-10 precision and MRR |
| 10. Adaptive orchestration | Completed (`adaptive_cutoff` selected) | 2 | Runtime-generated retrieval plan |
| 11. Tuning and ablations | Completed (`dense_off` retained) | 3 | Frozen robust configuration |
| 11B. Post-lockbox reranker research | Completed (experimental) | 3 | Bounded movement improved development only |
| 12. Reliability and performance | Completed | 3 | Offline-safe, valid responses |
| 13. Packaging and demo | Completed | 3 | Reproducible final submission |

## Target score gates

| Checkpoint | Hit Rate@10 | MRR | MTTC | TechnicalScore |
|---|---:|---:|---:|---:|
| Official starter | 0.125 | 0.0680 | 9.81 | 0.1067 |
| End of Day 1 target | >= 0.80 | Measure | <= 4.5 | >= 0.70 |
| Competitive Day 2 target | >= 0.90 | >= 0.65 | <= 3.5 | >= 0.78 |

These are development targets rather than guarantees. Prefer improvements that hold across scenario slices and a local lockbox.

## Hackathon scope decisions

The following job-alignment additions are small enough or score-relevant enough to include during the hackathon:

- **First-class Agent harness:** structured traces, replay, schema validation, timing, fallbacks, and experiment IDs. This extends Tasks 2 and 12.
- **Typed skill registry:** expose parsing, memory updates, lexical search, dense search, reranking, clarification, and validation as typed capabilities. This is a lightweight Python abstraction, not a new service.
- **Catalog knowledge ontology:** preserve the category hierarchy and extracted facets as the read-only knowledge base used by retrieval and verification.
- **Versioned context templates:** make the compiled retrieval/reranking context explicit and measurable. Use prompt versioning only if an LLM component is actually added.
- **Conditional LangGraph adapter:** after the deterministic orchestrator reaches the Day 2 score gate, time-box a thin graph adapter to two hours. The official Agent must continue to work without it.
- **Conditional offline contextual-bandit experiment:** after the heuristic recommendation policy reaches the Day 2 score gate, time-box a comparison to three hours. Keep it only if held-out TechnicalScore improves.

The following remain deliberately outside the three-day submission and are specified in `POST_HACKATHON_ROLE_ALIGNMENT_PLAN.md`:

- Production FastAPI service, Docker image, deployment, and load testing.
- Full LangGraph migration if the small adapter is not completed safely.
- Multi-agent planner/critic collaboration.
- Merchant Search Quality Analyst and creator/merchant workflows.
- Full offline RL training infrastructure and policy lifecycle.
- Comprehensive prompt operations, security testing, and production observability.

---

## Architecture

```text
Official Agent adapter
   |
   v
Agent harness
 schema validation • tracing • replay • timeouts • fallbacks
   |
   v
Deterministic orchestrator (optional thin LangGraph adapter)
   |
   v
Typed skill registry
   |
   +-- parse/update-memory skills
   +-- lexical/dense retrieval skills
   +-- rerank/verify skills
   `-- clarify/respond skills
   |
   v
Parser + event detector
   |-- Buying intent
   |-- Browsing intent
   |-- Override event
   `-- No-preference event
   |
   v
Versioned session state
   |-- active and superseded slots
   |-- stable category
   |-- profile priors
   |-- asked/no-preference attributes
   `-- previously shown products
   |
   v
Dynamic context compiler
   |
   v
Retrieval planner
   |-- fielded lexical routes
   |-- structured constraints
   |-- dense semantic route
   `-- route fusion
   |
   v
Confidence estimator + recommendation policy
   |-- overloaded/low confidence: 0–3 recommendations + clarify
   |-- medium confidence: 3–5 recommendations + clarify
   `-- high confidence/late turn: up to 10 recommendations
   |
   v
Optional semantic reranker
   |
   v
Contract-valid response
```

The framework layer is an adapter, not the source of business logic. Each skill must remain directly callable and testable so the official offline path does not depend on LangGraph.

### Hackathon skill contract

```python
class Skill(Protocol):
    name: str
    version: str

    def execute(self, context: SkillContext) -> SkillResult:
        ...
```

Every skill result should include its output, latency, warnings, and fallback status. Keep the registry small; it exists to make capabilities testable and orchestratable, not to imitate a large framework.

### Canonical session state

```python
SessionState(
    route="buying" | "browsing",
    category=...,
    slots=[
        Slot(
            attribute=...,
            value=...,
            source_turn=...,
            confidence=...,
            strength="hard" | "soft",
            status="active" | "superseded",
        )
    ],
    profile_priors=...,
    asked_attributes=...,
    no_preference_attributes=...,
    shown_product_ids=...,
    cached_candidates=...,
)
```

### Revised recommendation policy

Returning ten recommendations on every turn is not always optimal. A target returned at a weak rank ends the session and locks in that reciprocal rank. Delaying by one turn costs approximately `0.02` TechnicalScore through efficiency, but a large rank improvement can be worth more. Conversely, missing the target entirely is very expensive because Hit Rate has a `0.50` weight.

The agent must therefore select recommendation count dynamically:

| Situation | Recommended action |
|---|---|
| Specific Buying query with reliable hard constraints | Return up to 10, reranked best-first; ask only if a valuable slot is missing |
| Moderately specific request | Return 3–5 high-confidence products and ask the best clarification |
| Extremely vague Browsing request or overloaded pool | Apply retrieval cutoff; return 0–3 only if genuinely confident, then clarify immediately |
| Intent Override just received | Rebuild state and candidates before returning recommendations; allow previously shown products to reappear |
| Late turn or falling candidate recall | Return up to 10 and progressively explore unshown candidates |
| Model/retrieval failure | Return deterministic fallback candidates rather than invalid output |

Initial confidence signals:

- Number and strength of active constraints.
- Candidate-pool size after filtering.
- Agreement between lexical, dense, and structured routes.
- Score margin between top candidates and the remaining pool.
- Fraction of active slots satisfied by each top candidate.
- Current turn and remaining turn budget.

Initial policy rules should be deterministic. Thresholds must later be tuned by comparing `always_10`, `vague_3`, and `vague_0` ablations on the combined TechnicalScore.

### Intent Override invalidation policy

On an override:

1. Deactivate explicitly superseded slots; retain them only as audit history.
2. Preserve the category and other compatible, non-revoked slots.
3. Rebuild compiled query text without stale values.
4. Invalidate candidate lists, dense query vectors, compatibility scores, and reranker scores derived from stale values.
5. Clear or soften the previously-shown-product penalty so a target ignored before the official override can appear again.
6. If the user replaces the category or says to start over, clear all category-dependent conversational slots.

---

## Sequential tasks

## Task 0 — Understand the evaluation contract

- [x] Read `README.md`.
- [x] Read `docs/competition_specification.md`.
- [x] Read `docs/agent_api_contract.json`.
- [x] Trace `evaluate`, `initial_message`, and `customer_reply` in `evaluator/local_evaluator.py`.
- [x] Read the starter `Agent` implementation.

**Status:** Completed  
**Estimated time:** 60–90 minutes  
**Dependencies:** None

**Outcome:** Understand what enters and leaves the Agent and how every decision affects Hit Rate, MRR, and MTTC.

**Knowledge required:**

- `reset` initializes isolated session state.
- `respond` receives only the current user message, turn, and Top-K setting; memory must be maintained by the Agent.
- No recommendations on a turn means no hit on that turn. A later hit uses the later rank for MRR and the later turn for MTTC.
- The evaluator ends immediately on the first valid target hit.
- `ask_attribute`, not prose interpretation, controls which information the public simulator reveals.
- Intent Override sessions cannot score before the official override turn.

**How:** Manually trace one Buying, one Browsing, and one Override session through the evaluator.

**Alternatives:** None; this knowledge is foundational.

**Completion gate:** Explain the response contract, the three core metrics, dynamic recommendation truncation, and targeted override invalidation without referring back to the code.

## Task 1 — Reproduce and freeze the baseline

- [x] Create/activate a virtual environment.
- [x] Run the unit tests.
- [x] Run the official evaluator.
- [x] Save the baseline output without modifying official files.

**Status:** Completed  
**Estimated time:** 45 minutes  
**Dependencies:** Task 0

**Outcome:** Confirm the kit works and establish a trusted comparison point.

**Knowledge required:** A baseline is the unchanged system score; a unit test checks isolated behavior, while the evaluator tests complete sessions.

**How:**

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m unittest -v
python3 -m evaluator.local_evaluator --output results_baseline.json
```

Expected TechnicalScore: approximately `0.10671`.

**Alternatives:** `pytest` may be added later, but built-in `unittest` is sufficient.

**Completion gate:** Tests pass and local metrics match the published baseline.

## Task 2 — Build the experiment and diagnostics runner

- [x] Record aggregate and per-scenario metrics.
- [x] Record candidate Recall@50/100/200.
- [x] Record per-turn target rank, question, route, recommendation count, and latency.
- [x] Emit structured skill and orchestration traces with experiment/configuration IDs.
- [x] Add schema validation, replayable turn inputs, warning fields, and fallback indicators.
- [x] Reserve a stratified local lockbox.
- [x] Make experiments nameable and reproducible.

**Status:** Completed  
**Estimated time:** 2 hours  
**Dependencies:** Task 1

**Outcome:** Build a lightweight Agent harness that separates candidate-generation failures from ranking and conversation-policy failures and can replay individual sessions.

**Knowledge required:** Retrieval recall asks whether the target entered the candidate pool; ranking asks whether it reached the scored Top 10. An ablation changes one component at a time.

**How:** Add a script such as `scripts/benchmark.py` that writes a structured JSON artifact for every experiment. Define one trace schema shared by the benchmark runner and Agent skills so route decisions, skill calls, latency, exceptions, and fallbacks can be inspected turn by turn.

**Alternatives:** A notebook is faster for exploration but less reproducible.

**Completion gate:** One command produces named metrics, structured execution traces, replayable session inputs, diagnostic fields, and a failure list.

## Task 3 — Build the normalized product representation

- [x] 3.1 Define a versioned `Product`, `Catalog`, and `CategoryOntology` schema in `starter/catalog.py`.
- [x] 3.2 Add small normalization helpers for text, lists, nested details, numeric fields, and missing values.
- [x] 3.3 Extract controlled material and color facets while preserving original catalog text.
- [x] 3.4 Build category prefix relationships and product membership for every category path.
- [x] 3.5 Implement a read-only loader with stable product order, ID lookup, duplicate-ID validation, and 50,000-row support.
- [x] 3.6 Add `scripts/build_catalog_cache.py` to precompute normalized products and ontology metadata when the source checksum or schema/facet version changes.
- [x] 3.7 Add `scripts/inspect_catalog.py` for schema, cache validity, field-coverage, facet, category, and load-time diagnostics.
- [x] 3.8 Add focused unit tests in `tests/test_catalog.py`, including nested details, missing fields, aliases, ontology paths, cache invalidation, and duplicate IDs.
- [x] 3.9 Run the full catalog smoke check, all tests, and a benchmark regression check without modifying `starter/agent.py`.

**Status:** Completed  
**Estimated time:** 3–4 hours  
**Dependencies:** Task 2

**Outcome:** A predictable, versioned catalog knowledge base for lexical, dense, and structured retrieval.

**Knowledge required:** Normalization creates an internal view; it does not mutate the catalog. Field separation allows title/category matches to carry more weight than description matches. A lightweight ontology captures category hierarchy and controlled facets without requiring an external database.

**How:** Use simple dataclasses containing ASIN, title, categories, store/brand, price, features, flattened details, description, ratings, extracted materials/colors, and methods that produce field-specific, lexical, and dense-retrieval text. Build the ontology from category-path prefixes. Store derived normalized products, ontology metadata, and a manifest separately from the frozen source catalog; reuse them while the recorded source checksum and schema/facet versions still match. Never reject a product solely because price, description, or an optional facet is absent.

**Alternatives:** Dataclasses and normalized JSON/JSONL cache files are selected for clarity and inspectability. SQLite would load and query faster but adds another schema and migration surface; rebuilding everything at startup is simpler but repeats deterministic work. Keep controlled facet aliases as Python constants for the MVP. Avoid Pydantic, an ORM, or a multi-file catalog framework.

**Completion gate:** Every catalog row loads without error, produces fielded and combined text, maps into the category hierarchy, and uses a reproducibly versioned schema. A valid cache avoids normalization work and an invalid cache is detected. The source catalog remains unchanged, unit tests pass, diagnostics report exactly 50,000 unique products, and the unchanged starter benchmark retains its baseline score.

## Task 4 — Implement the versioned session state machine

- [x] 4.1 Define the state invariants and small typed structures in `starter/state.py`: `SlotValue`, `Slot`, `TurnMessage`, `ShownProduct`, and `SessionState`. Each grouped slot has `any`/`all` matching semantics, while every contained value has its own active/deactivated lifecycle and deactivation provenance.
- [x] 4.2 Add `SessionStore` lifecycle operations: `reset`, `get`, and `remove`, with strict isolation by `session_id` and a clean error for use before reset.
- [x] 4.3 Add turn recording with the raw user message, evaluator turn number, and monotonic-turn validation without interpreting the message text.
- [x] 4.4 Implement explicit slot operations for `add`, `replace`, and `clear`, preserving provenance, confidence, hard/soft strength, and superseded values for debugging.
- [x] 4.5 Implement no-preference tracking separately from slot values, including a mode that preserves an already disclosed value when the user says “no additional preference.”
- [x] 4.6 Implement override operations for targeted slot replacement, explicitly supplied dependent-slot invalidation, category replacement, and full restart.
- [x] 4.7 Add a search revision and cache invalidation mechanism so every meaningful state change invalidates derived query/candidate context without deleting audit history.
- [x] 4.8 Track shown products by search revision, including first/last turn, best rank, and display count, so later retrieval can discourage repetition and soften/reset that penalty after an override.
- [x] 4.9 Add compact immutable views for active constraints, `any`/`all` match modes, confidence, hard/soft strength, resolved no-preference attributes, current-revision shown IDs, and future retrieval/context construction.
- [x] 4.10 Add table-driven tests in `tests/test_state.py` for accumulation, replacement, category override, targeted invalidation, full restart, no preference, shown products, cache invalidation, turn validation, and cross-session isolation.
- [x] 4.11 Run all tests and the unchanged starter benchmark to confirm that this isolated state module introduces no retrieval-score regression.

**Status:** Completed  
**Estimated time:** 2.5–3.5 hours  
**Dependencies:** Task 3

**Outcome:** Robust information accumulation, override behavior, and boundary handling.

**Knowledge required:**

- A slot is a named preference such as `material`, `color`, or `budget`; it can contain one or more values.
- Provenance records which turn and message produced a value. Confidence describes extraction certainty, while strength describes whether the user treated it as hard or soft.
- Superseded values remain in history for diagnostics but are excluded from active retrieval context.
- No preference means an attribute is resolved and should not be asked again; it is not itself a product constraint.
- A search revision identifies one coherent recommendation phase. An override starts a new revision, allowing old shown-product history to remain available without penalizing the new search.
- The state machine applies typed updates only. Message parsing, intent detection, and deciding which update to issue belong to Task 5.

**Proposed structures:**

```python
SlotValue(value, normalized_value, confidence, strength, source_turn, source_text, active)
Slot(name, values, no_preference, updated_turn)
TurnMessage(turn, text)
ShownProduct(parent_asin, revision, first_turn, last_turn, best_rank, display_count)
SessionState(session_id, user_profile, slots, messages, shown_products, revision, context_version)
SessionStore(sessions)
```

**Update flow:**

```text
Task 5 parses message
    -> creates explicit state operation
    -> SessionState applies it
    -> active constraints change
    -> context_version increments
    -> derived caches clear
    -> retrieval receives a read-only active-state view
```

On a targeted override, deactivate only the named old value or slot and any dependent slots explicitly supplied by the caller. Do not guess broad invalidation inside the state module. On a full restart, deactivate all session constraints and no-preference markers while retaining the user profile and audit history. Start a new search revision for overrides/restarts so prior shown products do not receive the same repetition penalty.

**Alternatives considered:**

- Plain nested dictionaries require less code but make invalid states and accidental key mismatches easier; dataclasses are selected.
- Physically deleting replaced values is simpler but removes debugging evidence; inactive history is selected.
- Automatically clearing every slot on any override is safer against stale context but loses still-valid constraints; targeted invalidation plus an explicit full-restart operation is selected.
- Clearing shown-product history loses useful diagnostics; revision-scoped penalties are selected.
- Event sourcing would provide a complete replay model but is unnecessary for the MVP; a small mutation API plus preserved history is sufficient.

**Files to create or modify:**

- Create `starter/state.py`.
- Create `tests/test_state.py`.
- Update this plan after verification.
- Do not modify `starter/agent.py`, the evaluator, or retrieval behavior during Task 4; Task 5 will wire parsed messages into the state store.

**Completion gate:** All state transitions are deterministic and Python 3.9 compatible; tests cover every operation and invariant; no state leaks across session IDs; no-preference attributes are not asked repeatedly by future consumers; overrides exclude stale values without destroying audit history; current-revision shown IDs and active constraints are directly queryable; all existing tests pass; and the starter benchmark remains exactly at Hit Rate@10 `0.125`, MRR `0.068034`, MTTC `9.81`, and TechnicalScore `0.10671`.

## Task 5 — Implement message parsing, intent routing, and the initial skill registry

- [x] 5.1 Define the parser output contract in `starter/understanding.py`: `SlotUpdate`, `ConversationEvent`, `ParsedTurn`, `IntentDecision`, and `TurnUnderstanding`.
- [x] 5.2 Build a lightweight `CatalogVocabulary` from catalog category paths, controlled color/material aliases, and catalog brands without adding a second catalog scan during Agent startup.
- [x] 5.3 Implement deterministic extraction for category/audience, material, color, size, brand, price range, use case, style, and generic feature phrases, including the evaluator's structured constraint phrasing.
- [x] 5.4 Detect no-preference, no-additional-preference, targeted correction, generic intent override, category override, and full-restart events separately from Buying/Browsing intent.
- [x] 5.5 Implement confidence-scored Buying/Browsing routing using concrete constraints, specificity, purchase cues, exploration cues, and the accumulated active state.
- [x] 5.6 Add `MemoryUpdater` to translate parsed updates/events into Task 4 operations, including generic override removal of prior soft preferences while retaining category and unrelated hard constraints.
- [x] 5.7 Convert aggregate `user_profile` tags into low-confidence soft priors kept separate from explicit user constraints, so profile evidence can boost ranking later but never hard-filter products.
- [x] 5.8 Add a minimal typed capability registry in `starter/skills.py` with `SkillContext`, `SkillResult`, registration, lookup, execution, and trace metadata; register understanding and memory-update capabilities without an external agent framework.
- [x] 5.9 Wire the state store and registered capabilities into `starter/agent.py` while preserving the existing BM25 response behavior; expose route, events, active slots, confidence, and state version through `get_last_trace()`.
- [x] 5.10 Add table-driven tests in `tests/test_understanding.py` and `tests/test_skills.py` for rewording, ambiguous text, slot extraction, boundary replies, overrides, routing, profile priors, registry validation, and state integration.
- [x] 5.11 Run all tests, representative benchmark replays for every scenario, and the full unchanged-retrieval regression benchmark before beginning recommendation-policy work.

**Status:** Completed  
**Estimated time:** 3–4 hours  
**Dependencies:** Task 4

**Outcome:** Convert text turns into reliable state updates and a retrieval route while establishing the typed capability interface used by later retrieval skills.

**Knowledge required:**

- Intent is the current search strategy (`buying` or `browsing`); an event changes memory (`override`, `no_preference`, or `restart`). An override is therefore not a third retrieval route.
- Slot extraction converts text into explicit facts. The parser emits operations but does not directly mutate session state.
- Deterministic extraction combines regular expressions, phrase cues, catalog-controlled vocabularies, and category-path matching. It is reproducible, fast, and sufficient for the evaluator's pre-cleaned text.
- Confidence measures extraction/routing certainty. Strength measures the user's commitment (`hard` or `soft`). They are different signals.
- Explicit conversation facts outrank aggregate-profile priors. A profile tag such as `comfort` must never exclude a target that does not mention comfort.
- The capability registry is a small dictionary of typed local functions. It provides traceable composition for later orchestration; it is not an LLM tool-calling framework.

**Understanding flow:**

```text
raw user message + current StateView
    -> deterministic parser
       -> slot updates
       -> conversation events
    -> intent router
       -> buying/browsing + confidence + reasons
    -> MemoryUpdater
       -> explicit Task 4 state operations
    -> updated immutable StateView + trace
```

For category phrases such as `slippers for women`, match normalized message n-grams against catalog category labels, find canonical paths ending in `Slippers`, and use the `Women` audience match to disambiguate the path. The canonical path order always comes from the catalog, not message word order. For arbitrary simulator constraints following cues such as `A key requirement is:` or `what matters is:`, preserve meaningful unmatched text as a generic feature slot instead of discarding it.

For the evaluator's generic override message (`ignore my earlier preference`), start one new search revision, deactivate active soft values from the earlier preference while preserving category and unrelated hard constraints, then apply the newly extracted hard constraint. Explicit corrections such as `not black anymore; blue is fine` deactivate only the named value. Full-restart cues invoke `SessionState.full_restart`; none of these operations reset the evaluator turn number.

**Alternatives considered:**

- A structured LLM parser handles broader language but adds latency, cost, nondeterminism, and secret management; keep it as an optional fallback after deterministic performance is measured.
- spaCy or a trained intent classifier could improve unusual phrasing but is unnecessary for clean evaluator messages and adds dependencies.
- Dense category-label matching can later recover paraphrases not covered by aliases; begin with catalog paths, n-grams, singular/plural normalization, and a small explicit synonym map.
- A large orchestration framework would make a simple three-capability pipeline harder to debug; use a minimal in-process registry now and retain an upgrade path for Task 10.

**Files to create or modify:**

- Create `starter/vocabulary.py` for catalog-grounded category and brand matching.
- Create `starter/understanding.py` for parser contracts, extraction, routing, and the combined understanding result.
- Create `starter/memory.py` for translating understanding results into Task 4 state operations.
- Create `starter/skills.py` for the small typed registry.
- Create `tests/test_understanding.py` and `tests/test_skills.py`.
- Modify `starter/agent.py` only to initialize/use the state and understanding pipeline and expose traces; keep its current BM25 query and response contract unchanged.
- Update this living plan after implementation and verification.

**Completion gate:** Reworded category queries resolve to catalog paths without relying on word order; common structured slots and simulator constraint phrases are extracted with provenance; boundary and override messages produce correct events; routing returns deterministic intent, confidence, and reasons; explicit facts and profile priors remain separate; registered capabilities return typed results and useful traces; Agent sessions update independently; all existing tests pass; and core benchmark metrics remain at the starter baseline until retrieval changes in later tasks.

## Task 6 — Implement clarification, confidence, and recommendation-count policy

- [x] 6.1 Define policy contracts in `starter/policy.py`: `RetrievalSignals`, `RecommendationConfidence`, `ClarificationDecision`, `RecommendationDecision`, `PolicyDecision`, and a small versioned `PolicyConfig`.
- [x] 6.2 Extend `SessionState` with revision-scoped clarification history so the policy can record asked attributes, avoid repetition, and allow a previously invalidated attribute to be reconsidered after an override.
- [x] 6.3 Refactor the existing single-route BM25 call to retrieve a wider internal scored pool without changing its ordering; derive candidate-count and top-score-separation signals for the policy while leaving multi-route retrieval to Task 7.
- [x] 6.4 Implement a deterministic recommendation-confidence estimator using intent confidence, active hard/soft constraints, category specificity, candidate-pool saturation, score separation, turn number, and recent override state.
- [x] 6.5 Implement `QuestionPlanner` to select one unresolved, high-yield attribute using route-aware and coarse-category-aware priorities while excluding active, no-preference, and already-asked attributes.
- [x] 6.6 Implement over-generality detection and the dynamic recommendation-count policy: `0–3` for extremely vague early browsing, `3–5` for moderate confidence, and up to `10` for specific Buying, override recovery, or late-turn coverage; on later turns, stably prefer unshown products from the current search revision before backfilling repeated products.
- [x] 6.7 Generate deterministic response messages that correctly support clarification only, recommendations only, or both, and always emit an API-valid `ask_attribute`.
- [x] 6.8 Add named policy variants—`always_10`, `vague_3`, `vague_0`, and `dynamic_safe`—and expose the selected variant through the benchmark configuration and run manifest for reproducible ablations.
- [x] 6.9 Wire the selected policy into `starter/agent.py`, truncate only the returned list, record only actually shown products, and expose confidence components, clarification utility, recommendation limit, and policy reasons through `get_last_trace()`.
- [x] 6.10 Add table-driven tests in `tests/test_policy.py` plus state/Agent integration cases for Buying, Browsing, boundary, override, late turns, empty pools, top-k caps, repeated questions, and all policy variants.
- [x] 6.11 Run controlled development-split comparisons of all variants, inspect scenario-level MRR/Hit Rate/MTTC and recommendation-count distributions, and select the highest-scoring safe default without using the reserved lockbox for tuning.
- [x] 6.12 Run all tests and a full contract/reliability check; record the selected configuration and results before beginning multi-route retrieval.

**Status:** Completed  
**Estimated time:** 3–4 hours  
**Dependencies:** Tasks 4–5

**Outcome:** Apply retrieval cutoff to vague queries while preserving coverage on confident and late turns.

**Knowledge required:**

- Intent confidence from Task 5 answers “Buying or Browsing?” Recommendation confidence answers “How likely is the current ranking to be correct?” They must remain separate.
- Returning no recommendations produces no hit on that turn. It does not create a special MRR value; if a later turn hits, that later rank supplies MRR and that later turn supplies MTTC.
- The evaluator stops at the first eligible target hit. An early target at rank 9 therefore locks reciprocal rank at `1/9`; waiting for better context could improve rank but costs a turn and risks a complete miss.
- Asking a question and returning recommendations are independent. When the target is not found, `ask_attribute` controls the simulator's next response; the prose alone does not.
- A pool is over-general when it is saturated at the internal retrieval limit, current constraints are sparse, and leading scores are poorly separated. This is different from simply having many catalog products.
- No-preference markers resolve an attribute and prevent repeated questions. Asked-attribute history prevents repetition before an answer is parsed. Both should be scoped correctly across search revisions.

**Policy flow:**

```text
TurnUnderstanding + current StateView + scored BM25 pool
    -> recommendation-confidence estimator
    -> over-generality check
    -> QuestionPlanner chooses zero or one attribute
    -> recommendation-count policy chooses 0, 3, 5, or up to 10
    -> current-revision unshown candidates are preferred without disturbing their relative rank
    -> response message + ask_attribute + truncated recommendations
    -> record question and actually shown product IDs
```

The confidence estimator will use simple bounded components rather than a learned model. A specific leaf category, multiple explicit hard constraints, and a clearly separated leading result raise confidence. Explicit exploration language, a saturated pool, few active constraints, and a recent override lower it. Turn number changes risk tolerance: early turns may protect MRR, while turns 8–10 favor Hit Rate and therefore return up to ten.

The initial question priorities will be category-aware but intentionally small. Examples: shoes prioritize `material`, `size`, `budget`, then `color`; clothing prioritizes `size`, `style`, `material`, then `color`; jewelry prioritizes `budget`, `material`, then `style`; vague browsing prioritizes `category`, `use_case`, and `style`. The planner skips attributes already active, explicitly marked no preference, or already asked in the current search revision. Task 7 can later replace fixed priorities with candidate-pool information gain without changing the policy interface.

The default must be selected empirically. `always_10` remains the coverage control. `vague_3` tests early truncation while preserving some chance of a hit. `vague_0` tests strict cutoff. `dynamic_safe` combines confidence, turn, and override signals. If a dynamic variant does not beat the control on development TechnicalScore, keep `always_10` as the temporary default while retaining clarification and policy traces for retuning after Task 7.

**Alternatives considered:**

- Always returning ten maximizes immediate coverage but can lock poor MRR and does not demonstrate retrieval cutoff; retain it as the control.
- Always returning zero on vague turns protects MRR but can unnecessarily sacrifice MTTC and Hit Rate; test it only as an ablation.
- A learned conversion policy or contextual bandit could optimize the tradeoff, but 200 public sessions are insufficient and overfitting risk is high.
- Exact expected information gain from every candidate facet is attractive but depends on the structured candidate pool being built in Task 7. Use a compatible `RetrievalSignals` interface now and enrich it later.
- LLM-generated questions offer more varied prose but do not improve the simulator signal, which is driven by `ask_attribute`; deterministic templates are cheaper and reproducible.

**Files to create or modify:**

- Create `starter/policy.py`.
- Create `tests/test_policy.py`.
- Modify `starter/state.py` and `tests/test_state.py` for clarification history.
- Modify `starter/agent.py` to produce scored internal candidates and apply the policy.
- Modify `benchmarking/models.py`, `benchmarking/runner.py`, and `scripts/benchmark.py` only as needed to select and record named policy variants reproducibly.
- Update this living plan after implementation and verification.

**Implementation result (2026-08-28):**

| Development variant | Hit@10 | MRR | MTTC | TechnicalScore |
|---|---:|---:|---:|---:|
| `always_10` | 0.4000 | 0.299147 | 8.0750 | **0.348244** |
| `dynamic_safe` | 0.38125 | 0.296629 | 8.2625 | 0.334364 |
| `vague_3` | 0.3750 | 0.295067 | 8.3250 | 0.329520 |
| `vague_0` | 0.34375 | 0.273192 | 8.61875 | 0.301458 |

`always_10` is the temporary default because the single-route Task 6 ranker still benefits more from coverage than from early truncation. The other policies remain reproducible and will be retuned after Task 7 raises candidate and rank quality. The verified development artifact is `experiments/runs/20260828T074733Z_task6_always10_verified` with zero exceptions, fallbacks, or warning turns. All 54 tests pass. The official evaluator over all 200 public sessions reports Hit@10 `0.42`, MRR `0.29479`, MTTC `7.86`, and TechnicalScore `0.361237`.

Post-Task-7 retuning confirmed this choice: with structured multi-route retrieval, `dynamic_safe` scored `0.542545` and `always_10` scored `0.545402`. Keep `always_10` as the current default.

**Completion gate:** Every response remains contract-valid; recommendation confidence is distinct from intent confidence and fully traced; no resolved or current-revision attribute is asked repeatedly; overrides scope question and shown-product history correctly; the returned list never exceeds evaluator `top_k`; late turns preserve coverage; all variants are reproducible from benchmark artifacts; all tests pass with zero reliability warnings; and the selected default beats or matches `always_10` on development TechnicalScore or is explicitly kept as the safer temporary control until Task 7.

## Task 7 — Implement multi-route lexical retrieval and fusion

- [x] 7.1 Freeze Task 6 as the retrieval control and define the Task 7 contracts in `starter/retrieval.py`: `LexicalQuery`, `RouteResult`, `CandidateEvidence`, `RetrievalResult`, and a small `RetrievalConfig`.
- [x] 7.2 Retain normalized `Product` objects and lightweight inverted lookups during the existing catalog scan, without adding a second startup scan or mutating the source catalog.
- [x] 7.3 Implement a `QueryCompiler` that turns the current message and active `StateView` into distinct query texts for current-message, category, latest-constraint, complete-state, title-heavy, and feature-heavy routes. Exclude inactive values and no-preference markers.
- [x] 7.4 Move fielded SQLite FTS execution behind a `LexicalRetriever` with per-route BM25 field weights, bounded route depth, stable ordering, and isolated route failure handling.
- [x] 7.5 Implement structured candidate lookup and compatibility scoring for exact category, audience, material, color, brand, and price constraints. Treat missing product metadata as unknown rather than a contradiction, so incomplete catalog fields do not erase recall.
- [x] 7.6 Implement deterministic weighted Reciprocal Rank Fusion (RRF), retaining every candidate's route ranks and contributions for inspection and using stable catalog order as the final tie-breaker.
- [x] 7.7 Add the first dual-track routing configuration: Buying emphasizes complete-state, latest-constraint, title, and structured compatibility; Browsing emphasizes category, current-message, feature, and route diversity.
- [x] 7.8 Integrate progressive exploration without duplicating policy logic: preserve the complete fused ordering, pass it to Task 6, and verify that the existing current-revision unshown-first selection and late-turn backfill work with the new pool.
- [x] 7.9 Register `retrieve_lexical` as a typed skill and wire its `RetrievalResult` into `Agent`; preserve the current single-BM25 path as a deterministic fallback.
- [x] 7.10 Extend traces and benchmark artifacts with compiled query summaries, route candidate IDs, route contribution counts, fused scores, compatibility evidence, retrieval configuration name, and fallback warnings.
- [x] 7.11 Add reproducible retrieval variants—`single_bm25`, `multi_route_rrf`, and `multi_route_structured`—to the benchmark CLI and manifest so fusion and structured scoring can be ablated independently.
- [x] 7.12 Add focused tests in `tests/test_retrieval.py` and integration tests for query compilation, field weights, RRF math, duplicate candidates, grouped-slot semantics, missing metadata, Buying/Browsing route weights, override cleanup, empty routes, fallback behavior, stable ties, and top-k compliance.
- [x] 7.13 Run development-only comparisons in stages: candidate recall first, then Hit@10/MRR/MTTC/TechnicalScore and latency by scenario. Inspect failures where the target is absent from the fused Top 200 separately from targets retrieved but ranked below 10.
- [x] 7.14 Select the best safe retrieval default, rerun all tests and the official contract check, record results here, and leave the lockbox unused for Task 11.

**Status:** Completed  
**Estimated time:** 4–5 hours  
**Dependencies:** Tasks 3–6

**Outcome:** High-recall lexical candidate generation that responds to session state.

**Knowledge required:**

- **Inverted index:** SQLite FTS stores which products contain each term, allowing retrieval without scanning all 50,000 product texts on every turn.
- **BM25:** Produces one relevance ordering for one query and one set of field weights. Title/category matches can therefore matter more than description matches.
- **Retrieval route:** One deliberately different view of the same need. For example, the category route protects catalog scope while the latest-constraint route reacts strongly to newly disclosed information.
- **RRF:** Combines route ranks using `weight / (k + rank)`. It is preferable to adding raw BM25 scores because scores from differently weighted queries are not directly comparable.
- **Structured compatibility:** Checks normalized facts such as category, material, color, brand, and price after lexical recall. It boosts verified matches and penalizes explicit contradictions, but does not reject products whose metadata is missing.
- **Candidate recall versus final ranking:** Recall@200 asks whether the target entered the fused pool. Hit@10 and MRR depend on promoting that target into the returned list. Task 7 must diagnose these separately.

**Planned flow:**

```text
current message + active StateView + Buying/Browsing route
    -> QueryCompiler
       -> current-message query
       -> category query
       -> latest-constraint query
       -> complete-state query
       -> title-heavy query
       `-> feature-heavy query
    -> fielded BM25 execution per non-empty route
    -> structured category/facet candidate lookup
    -> weighted RRF union
    -> compatibility boosts and contradiction penalties
    -> stable fused Top 200 + per-candidate evidence
    -> Task 6 recommendation and clarification policy
    -> API-valid response
```

**Route behavior:**

| Route | Query source | Main purpose |
|---|---|---|
| Current message | Terms from the latest user reply | React immediately to new information |
| Category | Active canonical category and audience | Preserve product scope across short follow-up replies |
| Latest constraint | Active values whose source turn is current | Give newly disclosed requirements strong influence |
| Complete state | Category plus every active slot | Represent the accumulated multi-turn need |
| Title-heavy | Complete-state terms, strongest title/category weights | Improve exact product-type precision |
| Feature-heavy | Feature, use-case, style, material, and current terms | Recover descriptive or scenario-based matches |
| Structured | Category/facet inverted lookups | Recover products through normalized metadata rather than word ranking alone |

Buying and Browsing do not invoke two completely separate systems. They select different weights and depths over the same tested routes. This keeps the implementation small while satisfying dual-track behavior. Overrides require no special retrieval parser: the state machine has already removed stale active values, so recompiling from `StateView` naturally excludes them.

**Implementation boundaries:**

- Create one main module, `starter/retrieval.py`; avoid a package of tiny retrieval files until the design proves too large.
- Continue using in-memory SQLite FTS and Python dictionaries. Do not add Elasticsearch, a vector database, an ORM, an LLM call, or a new service.
- Reuse the existing catalog scan to build normalized product metadata and structured indexes.
- Keep route limits around 100–200 and the fused pool at 200 initially. Measure before increasing them.
- Keep Task 6's selected `always_10` recommendation policy fixed during retrieval comparisons so only retrieval changes.
- Do not implement dense embeddings or semantic reranking in this task; those remain Tasks 8 and 9.

**Alternatives considered:**

- **Raw normalized score addition:** simpler mathematically, but normalization can be unstable when BM25 distributions differ across routes. RRF is safer for the first version.
- **Hard filtering all explicit constraints:** precise when metadata is complete, but dangerous for products with missing or inconsistently represented fields. Use contradiction-aware soft penalties and reserve strict filtering for fully reliable fields/configured experiments.
- **Scanning all products each turn:** easy to write, but unnecessary. Precomputed category/facet indexes and FTS keep runtime light.
- **One giant accumulated query:** simpler, but new details can be diluted and category context can disappear on follow-up turns. Separate routes preserve both signals.
- **Learned fusion:** potentially stronger, but 160 development sessions are too few for safe training. Start with explicit route weights and ablations.

**Planned files:**

- Create `starter/retrieval.py` and `tests/test_retrieval.py`.
- Modify `starter/agent.py` to initialize and call the retriever.
- Modify `starter/skills.py` to register the lexical retrieval capability.
- Modify `benchmarking/models.py`, `benchmarking/runner.py`, `benchmarking/reporting.py`, and `scripts/benchmark.py` for retrieval variants and route diagnostics.
- Modify existing Agent/benchmark tests only where integration behavior changes.
- Update this plan with measured ablations and the selected default.

**Implementation result (2026-08-28):**

| Development configuration | Recall@200 | Hit@10 | MRR | MTTC | TechnicalScore |
|---|---:|---:|---:|---:|---:|
| `single_bm25 + always_10` | 0.7625 | 0.4000 | 0.299147 | 8.0750 | 0.348244 |
| `multi_route_rrf + always_10` | 0.84375 | 0.64375 | 0.335007 | 6.7500 | 0.507377 |
| `multi_route_structured`, depth 200 | 0.8625 | 0.7000 | 0.319382 | 6.19375 | 0.541940 |
| `multi_route_structured`, depth 400 | **0.8625** | **0.7000** | 0.329673 | **6.1750** | **0.545402** |
| depth 400 + `dynamic_safe` policy | 0.8625 | 0.6875 | **0.369732** | 6.60625 | 0.542545 |

The selected default is `multi_route_structured` with route depth 400 and the `always_10` policy. It wins the combined score while the dynamic policy remains available for later tuning. The verified development artifact is `experiments/runs/20260828T092047Z_task7_structured_depth400`, with mean turn latency `108.12 ms`, zero exceptions, zero fallbacks, and zero warning turns.

The fused lexical Recall@200 target of `0.97–0.98` was not reached. Recall improved materially from `0.7625` to `0.8625`, while the union of all route candidates reached `0.9125`. The remaining targets lack sufficient lexical/structured evidence or do not survive fusion; Task 8 dense retrieval is the appropriate next mechanism rather than adding more lexical heuristics.

The official evaluator over all 200 public sessions reports Hit@10 `0.695`, MRR `0.327327`, MTTC `6.15`, and TechnicalScore `0.542698`. All 64 tests pass, compilation and whitespace checks are clean, and the official response contract remains valid.

**Completion gate:** All responses remain contract-valid; stale slots never enter compiled queries after override; route and RRF behavior are deterministic; one failed route falls back without losing the whole response; candidate evidence explains why a product ranked where it did; development Candidate Recall@200 materially improves from Task 6's `0.7625` and approaches the `0.97–0.98` target if lexical evidence permits; overall TechnicalScore improves over `0.348244` on the development split; latency and reliability remain acceptable; all tests pass; and no lockbox sessions are used for tuning.

## Task 8 — Add dense semantic retrieval

- [x] 8.1 Upgrade the project runtime to Python 3.12, add `.python-version` and `pyproject.toml`, rebuild `.venv` with the locally available Python 3.12.14 through `uv`, and lock NumPy, PyTorch, Transformers, and the current Sentence Transformers release.
- [x] 8.2 Use `BAAI/bge-small-en-v1.5` as the primary encoder, record its complete runtime metadata, and retain `sentence-transformers/all-MiniLM-L6-v2` as an unbuilt fallback option after BGE's small measured contribution made a second full-catalog encoding unjustified.
- [x] 8.3 Define dense contracts in `starter/dense.py`: `DenseConfig`, `EmbeddingManifest`, `DenseQuery`, `DenseResult`, and a small encoder protocol so retrieval tests can use a fake encoder without loading the real model.
- [x] 8.4 Implement a versioned `DenseDocumentCompiler` using the existing `Product.dense_text`: title, canonical category, brand, features, and concise description. Keep one deterministic template and cap text before model truncation.
- [x] 8.5 Implement `scripts/build_embeddings.py` to batch-encode all 50,000 products once, L2-normalize the vectors, and atomically save the embedding matrix, ordered ASIN list, manifest, and checksums under `data/cache/embeddings/`.
- [x] 8.6 Validate embedding-cache alignment before runtime: catalog checksum, product count/order, model ID/revision, document-template version, dimension, dtype, and normalization flag must all match. Never silently reuse stale vectors.
- [x] 8.7 Implement a `DenseQueryCompiler` that distills only the current message and active state into a shopping query. Add BGE's retrieval instruction to queries, add no instruction to product documents, and exclude deactivated/no-preference values.
- [x] 8.8 Implement `DenseRetriever` using exact normalized dot-product search with NumPy. Load the on-disk `float16` matrix into a reusable in-memory `float32` matrix, use `argpartition` plus stable score sorting, and initially retrieve 400 dense candidates.
- [x] 8.9 Extend the existing fusion path so the dense route participates in weighted RRF without discarding lexical route evidence or structured compatibility. Start with a lower dense weight for Buying and a higher weight for Browsing.
- [x] 8.10 Register `retrieve_dense` as a typed skill and add hybrid execution to `Agent`. Missing dependencies, model files, invalid caches, or inference failures must warn and fall back to the selected Task 7 lexical pipeline.
- [x] 8.11 Extend traces and benchmark artifacts with dense query version, model/revision, device, encode latency, dense candidate IDs/scores, dense target rank, hybrid contributions, cache status, and fallback reason.
- [x] 8.12 Add reproducible dense variants—`dense_off`, `dense_only`, and `hybrid_dense`—while holding Task 7's `multi_route_structured` retrieval and `always_10` policy fixed during the main ablation.
- [x] 8.13 Add unit and integration tests for document/query compilation, stale-slot removal, cache validation, ASIN alignment, normalized vectors, exact Top-K, stable ties, dense/lexical fusion, route weighting, missing-model fallback, offline-only loading, and response-contract compliance.
- [x] 8.14 Run development experiments in stages: dense-only Recall@200, lexical/dense union recall, hybrid fused Recall@200, scenario-level Hit@10/MRR/MTTC/TechnicalScore, model startup, query latency, and memory. Select dense retrieval only if it adds robust value.
- [x] 8.15 Freeze the winning model/configuration, verify a fresh offline process can load it without network access, run all tests and the official evaluator, record results here, and leave the lockbox unused until Task 11.

**Status:** Completed — dense implementation retained, `dense_off` selected by ablation  
**Estimated time:** 4–6 hours, including model download and one-time catalog encoding  
**Dependencies:** Task 7

**Outcome:** Recover semantic matches that do not share literal query terms.

**Knowledge required:**

- **Embedding:** A fixed-length numeric representation of text. Semantically related text can be close even when it shares few exact words.
- **Bi-encoder:** The same model encodes the query and every product independently. Product vectors can therefore be precomputed once rather than recomputed per session.
- **Normalization:** Dividing every vector by its length makes dot product equal cosine similarity. Larger scores then indicate greater semantic similarity.
- **Exact dense search:** For one query, compute one matrix-vector multiplication against all 50,000 products. At this catalog size, exact NumPy search is simpler and safer than an approximate index.
- **Hybrid recall:** Dense retrieval should add candidates missing from lexical routes. RRF then combines independent rank evidence without directly adding incompatible cosine and BM25 scores.
- **Model cache versus embedding cache:** Model weights are required to encode new queries; product embeddings are the already-computed catalog vectors. Both must be locally available for fully offline evaluation.
- **Model revision:** A model name such as `bge-small-en-v1.5` can still change upstream. Pinning the resolved commit and recording it in the embedding manifest makes the artifact reproducible.

**Selected model:**

`BAAI/bge-small-en-v1.5` is the primary choice because it is a small English retrieval model with 384-dimensional embeddings and a 512-token limit. Its model card recommends a retrieval instruction for short-query-to-passage search and no instruction for passages. The matrix sizes are approximately:

| Representation | Calculation | Approximate size |
|---|---:|---:|
| Disk cache, `float16` | 50,000 × 384 × 2 bytes | 38.4 MB |
| Runtime matrix, `float32` | 50,000 × 384 × 4 bytes | 76.8 MB |

`all-MiniLM-L6-v2` remains the fallback comparison because it is smaller and simple, but it truncates inputs at 256 word pieces and is a general sentence-similarity model rather than the selected retrieval-focused default. `e5-small-v2` is also viable, but it requires strict `query:`/`passage:` prefixes and does not offer enough expected advantage to justify a third full-catalog encoding during the hackathon.

**Planned flow:**

```text
One-time preparation
Product.dense_text for 50,000 products
    -> pinned local BGE encoder in batches
    -> normalized 384-d vectors
    -> float16 matrix + ASIN order + versioned manifest

Runtime per turn
current message + active StateView
    -> DenseQueryCompiler
    -> one normalized query vector
    -> exact matrix dot product
    -> dense Top 400
    -> weighted RRF with Task 7 lexical/structured routes
    -> hybrid Top 200
    -> Task 6 recommendation policy
```

The query will resemble the following structured text before encoding:

```text
Represent this sentence for searching relevant passages:
Shopping request. Category: women's hiking boots.
Requirements: waterproof; leather; size 8.
Current request: I need something suitable for winter trails.
```

This is dynamic context programming rather than transcript embedding: only active facts are compiled, stale override values are absent, and the current request remains visible.

**Dependency and offline strategy:**

- The current shell defaults to Python 3.9.6, but the repository recommends Python 3.10 or later and has no rule requiring Python 3.9. Python 3.12.14 and `uv` are already installed locally.
- Standardize the project on Python 3.12 using `.python-version`, declare the supported version in `pyproject.toml`, and recreate the project `.venv` with `uv venv --python 3.12`.
- Use the current Sentence Transformers release rather than maintaining an older Python-3.9-compatible dependency branch. Resolve NumPy, PyTorch, Transformers, Sentence Transformers, and their transitive dependencies once, then commit `uv.lock` for reproducibility.
- Run the existing 64 tests immediately after the runtime upgrade, before adding dense code. If they fail, fix only genuine Python 3.12 compatibility problems and preserve evaluator behavior.
- Document Python 3.12 as the tested submission runtime, as required by the competition submission rules for a non-default environment.
- Download the pinned model during preparation, save it to a configured local model directory, and use local/offline loading during evaluation.
- The official Agent must continue with lexical retrieval if NumPy, the model, or embeddings are unavailable. It must never attempt a network download during `respond()`.

**Fusion strategy:**

| Intent | Initial lexical/structured behavior | Initial dense behavior |
|---|---|---|
| Buying | Preserve stronger exact constraints and structured verification | Lower weight; recover paraphrases without overriding hard evidence |
| Browsing | Preserve category and scenario routes | Higher weight; favor semantic scenario and cross-wording matches |
| Override turn | Recompile from the new active revision | Re-encode without stale preferences |
| Late turn | Preserve broad lexical coverage | Allow deeper dense candidates into the fused pool |

Task 8 adds candidates, not final semantic reranking. Task 9 remains responsible for more expensive query-product pair scoring and improving MRR inside the candidate pool.

**Alternatives considered:**

- **FAISS:** useful for millions of vectors, but unnecessary for 50,000 × 384 exact search. Add it only if measured NumPy latency is unacceptable.
- **ONNX Runtime:** potentially reduces PyTorch runtime overhead, but adds export/provider complexity. Keep it as the first performance fallback if Torch CPU inference is too slow.
- **External embedding API:** avoids local model installation but violates the preferred offline/reproducible path and introduces credentials, cost, and rate limits.
- **Encoding products at Agent startup:** simpler artifact management but far too slow and repeats deterministic work. Precompute once.
- **Embedding the full transcript:** easy but carries stale and irrelevant turns. Compile active state instead.
- **Storing only `float16` in memory:** saves roughly 38 MB, but CPU matrix multiplication may be slower or less predictable. Store `float16` on disk and compare runtime `float32` loading.

**Planned files:**

- Create `starter/dense.py`, `scripts/build_embeddings.py`, and `tests/test_dense.py`.
- Add `.python-version`, `pyproject.toml`, and `uv.lock` as the canonical project runtime and dependency definitions.
- Modify `starter/retrieval.py` to accept the dense route in fusion.
- Modify `starter/skills.py` and `starter/agent.py` for typed dense execution and lexical fallback.
- Modify benchmark models, runner, reporting, and CLI for dense variants and diagnostics.
- Extend `.gitignore` only for downloaded model/cache artifacts that should not be committed.
- Update this plan with model revision, artifact checksums, measured memory/latency, ablations, and selected defaults.

**Implementation result:**

- The project now uses Python `3.12.14` with a committed `uv.lock`: NumPy `2.5.2`, PyTorch `2.13.0`, Transformers `5.16.1`, and Sentence Transformers `6.0.0`.
- The primary encoder is `BAAI/bge-small-en-v1.5` revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`, MIT licensed, 384 dimensions, 512-token maximum, and CPU device. Document template v3 caps deterministic product text at 512 characters.
- The one-time 50,000-product build took `5m 19s`. The local model is approximately `128 MB`; the float16 cache is approximately `37 MB`. Embedding checksum: `3b7bbdb2a688ec62ecd993e83109fe5a7c28ec880042c351c489766b004d7b39`. ASIN-order checksum: `b155fd18119a0c0007c0258a4ce560092ffd7748aec6fde607555f4415823d81`.
- A fresh forced-offline process loaded successfully with no warnings or fallbacks. Measured startup was `8.832s`; one representative hybrid turn was `291ms`, including `175ms` query encoding.
- Dense-only development results: Recall@200 `0.55`, Hit@10 `0.375`, MRR `0.234953`, MTTC `8.5375`, TechnicalScore `0.307236`, mean turn latency `120.17ms`.
- Hybrid development results: Recall@200 `0.85`, Hit@10 `0.68125`, MRR `0.304477`, MTTC `6.49375`, TechnicalScore `0.522093`, mean turn latency `114.68ms`.
- On the hybrid conversations, the union of all lexical routes recalled `0.9125`; adding dense raised raw route-union recall to only `0.91875`, a `0.00625` addition rate. That complementarity is real but too small to compensate for weaker fused ranking.
- Task 7 therefore remains the selected submission path with `dense_off`. Dense retrieval remains reproducible and available for Task 9 candidate/reranking experiments, but it is not marketed as the winning default.
- All `73` tests pass. The untouched lockbox was not used. The official 200-session evaluator on the selected default remains Hit@10 `0.695`, MRR `0.327327`, MTTC `6.15`, and TechnicalScore `0.542698`.

**Completion gate:** The artifact, offline, determinism, fallback, tracing, testing, and contract gates passed. Dense added one development-session route-union hit but failed the score-selection gate, so the guarded selection rule correctly retained `dense_off` rather than shipping a regression.

## Task 9 — Add semantic cross-encoder reranking

- [x] 9.1 Freeze Task 7 as the control and calculate reranking ceilings at candidate depths 20, 40, 60, and 100 from existing development traces.
- [x] 9.2 Define typed reranking contracts in `starter/reranking.py`: `RerankerConfig`, `RerankQuery`, `RerankCandidate`, `RerankResult`, `RerankerManifest`, and a `PairScorer` protocol.
- [x] 9.3 Implement versioned `RerankQueryCompiler` and `RerankDocumentCompiler` classes using only the current message, active state, and concise product fields.
- [x] 9.4 Implement `scripts/prepare_reranker.py` to resolve and save pinned local copies of MiniLM L4 and L6 with revision, license, size, library version, device, and maximum-length metadata.
- [x] 9.5 Implement a local-only `CrossEncoderScorer` adapter that batches query-product pairs, returns one finite score per candidate, and never downloads inside `Agent.respond()`.
- [x] 9.6 Implement `SemanticReranker` to rerank only the first configured N candidates and append the unscored tail in its original deterministic order.
- [x] 9.7 Add rank-based blending between first-stage retrieval rank, semantic rank, and existing structured compatibility. Do not directly add raw cross-encoder logits to BM25 or RRF scores.
- [x] 9.8 Register `rerank_candidates` as a typed skill and integrate it after retrieval but before recommendation policy. Any model, input, or inference failure must return the exact Task 7 ranking.
- [x] 9.9 Add reproducible variants `rerank_off`, `minilm_l4_semantic`, `minilm_l4_blended`, and `minilm_l6_blended`, plus explicit rerank depth and batch-size benchmark settings.
- [x] 9.10 Extend traces and benchmark artifacts with compiled-query version, model/revision, depth, batch size, pre/post target rank, rank movement, semantic scores/ranks, blend contributions, latency, and fallback reason.
- [x] 9.11 Add fake-scorer unit and integration tests for stale-slot removal, pair compilation, stable ties, bounded-head reranking, untouched-tail order, score/rank blending, hard-constraint preservation, malformed scorer output, offline loading, fallback, and API-contract compliance.
- [x] 9.12 Microbenchmark L4 and L6 on the actual CPU with candidate depths 20/40/60/100 and batch sizes 16/32/64 before launching expensive simulator runs.
- [x] 9.13 Run staged development ablations: a small deterministic pilot first, then the full 160-session development split only for configurations that pass the latency and pilot-score gates. Keep `multi_route_structured`, `dense_off`, and `always_10` fixed.
- [x] 9.14 Select a reranker only if it improves MRR and TechnicalScore without materially reducing Hit@10 or reliability. Otherwise retain `rerank_off` and record the negative result.
- [x] 9.15 Freeze the winning configuration, verify a fresh forced-offline process, run all tests and the official evaluator, record the measurements here, and leave the lockbox unused until Task 11.

**Status:** Completed — MiniLM L4 blended reranker selected  
**Estimated time:** 4–6 hours, including two model downloads and staged evaluation  
**Dependencies:** Task 8

**Outcome:** Promote targets from the high-recall candidate pool into the Top 10 and toward rank 1.

**Knowledge required:**

- **First-stage retriever:** Task 7 cheaply searches all 50,000 products and returns a high-recall ordered pool. Its job is coverage, not perfect ordering.
- **Cross-encoder:** A transformer reads the query and one candidate together and emits a relevance logit. This captures word interactions that BM25 and independently computed embeddings miss, but every candidate requires model inference.
- **Not a generative LLM:** MiniLM does not write text, call an API, use tool-calling, or consume chat tokens. It is a local supervised relevance scorer.
- **Rerank ceiling:** If the target is not inside the first N candidates, a depth-N reranker cannot recover it. Candidate Recall@N is therefore the maximum session coverage that reranking can influence.
- **Raw score versus rank:** Cross-encoder logits are not calibrated against BM25 or RRF values. Convert each signal to a rank and combine rank evidence, or normalize it within the current candidate list.
- **Head and tail:** Only the bounded candidate head is model-scored. Products after that head retain their original order so semantic inference cannot accidentally erase candidate coverage.
- **Offline model cache:** Model weights and tokenizer files must be downloaded during preparation, pinned to a commit, and loaded from a local directory with network access disabled at runtime.

**Starting configuration:**

Task 9 starts from the winning Task 7 pipeline:

```text
multi_route_structured + always_10 + dense_off
```

Dense retrieval is not required because Task 8's hybrid path reduced TechnicalScore and added only one raw route-union hit on the development split. After lexical reranking works, one optional `hybrid_dense + reranker` experiment may be run only if time remains; it must not replace the controlled lexical-first comparison.

**Planned architecture:**

```text
Current message + active StateView
    -> RerankQueryCompiler v1

Task 7 lexical/structured Top 200
    -> take configurable head N (initially 40)
    -> compile N concise product documents once in memory
    -> local CrossEncoder.predict(query, product) in batches
    -> semantic rank for N candidates
    -> weighted rank fusion with retrieval rank
    -> preserve structured compatibility evidence
    -> append candidates N+1..200 unchanged
    -> RecommendationPolicy

Any failure
    -> exact original Task 7 ranking
```

Example pair sent to the scorer:

```text
Query:
Shopping request. Category: women's hiking boots. Requirements: waterproof,
leather, size 8. Current request: I need something for winter trails.

Candidate:
Title: Women's Waterproof Leather Hiking Boot
Category: Clothing > Women > Shoes > Outdoor > Hiking Boots
Brand: Example
Features: insulated lining; high-traction rubber sole; waterproof upper
```

No stale value from an earlier search revision may appear in the query. Product text is compiled once at Agent startup because the frozen catalog never changes; query text is compiled each turn because active conversation state does change.

**Sequential implementation details:**

1. **Measure the available ceiling before coding the model.** Read the Task 7 development traces and report how often the purchased ASIN appears within candidate ranks 20, 40, 60, and 100. This determines whether a deeper reranker can possibly justify its latency. If Recall@40 is already close to Recall@100, prefer 40; otherwise microbenchmark both.
2. **Create contracts independent of Sentence Transformers.** `PairScorer` accepts text pairs and returns scores. Tests will inject a tiny fake scorer, making ranking logic fast, deterministic, and testable without model weights.
3. **Compile minimal active context.** The query compiler includes canonical category, audience, active hard/soft constraints, and the current request. It excludes inactive audit history, no-preference attributes, full transcripts, profile tags presented as facts, and BGE's query instruction because the cross-encoder was not trained to require it.
4. **Compile concise candidate evidence.** Use title, canonical category, brand, leading features, and a short description. Keep a stable character/token budget so the product evidence is not unpredictably truncated after the query-product pair is tokenized.
5. **Prepare pinned models outside runtime.** Download L4 and L6 once, save each locally, and write a manifest. Start performance work with L4 because it is smaller/faster; advance L6 only if its measured quality gain can justify its CPU cost.
6. **Score a bounded head in batches.** Build `(query, candidate_text)` pairs for the first N retrieval candidates, call the local scorer once per batch, validate output length and finite numbers, then sort by descending semantic score with original retrieval rank as the tie-breaker.
7. **Blend cautiously.** First run `semantic_only` as a diagnostic. The submission candidate should use weighted reciprocal ranks, initially retrieval `1.0` and semantic `0.5`, while carrying structured compatibility and contradiction evidence forward. Tune only semantic weight from a small set such as `0.25`, `0.5`, `0.75`, and `1.0`.
8. **Protect the fallback path.** Reranking is optional. A missing directory, incompatible manifest, malformed output, timeout, or inference exception must add a trace warning and preserve the byte-for-byte candidate order produced by Task 7.
9. **Keep experiments controlled.** Main ablations change one variable at a time: model, depth, batch size, then blend weight. Do not simultaneously enable dense retrieval, dynamic policy changes, or Task 10 orchestration.
10. **Select on score and feasibility together.** The preferred configuration must improve development MRR and TechnicalScore, maintain Hit@10, produce zero contract failures, and fit an initial target of mean turn latency below `500 ms` and p95 below `1 s` on the current CPU. These latency limits can be tightened after microbenchmarking.

**Model order:**

1. `cross-encoder/ms-marco-MiniLM-L4-v2` is the first implementation target. Its official model repository provides a 4-layer, 384-hidden-size ranker, Apache-2.0 license, safetensors weights of roughly 76.7 MB, and direct Sentence Transformers `CrossEncoder.predict()` usage.
2. `cross-encoder/ms-marco-MiniLM-L6-v2` is the quality challenger. Its official weights are roughly 90.9 MB. Published model-card measurements show a modest ranking-quality improvement but lower throughput than L4; those throughput figures were measured on a V100 GPU, so local CPU measurements decide the hackathon choice.
3. Do not download L12, a generative model, or additional rerankers unless both planned models fail and enough time remains. More model choices increase tuning risk on only 160 development sessions.

**Experiment matrix:**

| Stage | Model | Depth | Blend | Purpose |
|---|---|---:|---|---|
| Control | Off | — | Task 7 order | Confirm `0.545402` development TechnicalScore |
| Logic check | Fake scorer | 10 | Semantic only | Verify contracts, ordering, tail, and fallback |
| Microbenchmark | L4 | 20/40/60/100 | None | Choose feasible depth and batch size |
| Pilot | L4 | Chosen depth | Semantic only | Detect model/domain mismatch cheaply |
| Pilot | L4 | Chosen depth | Retrieval + semantic rank | Choose guarded blend weight |
| Challenger | L6 | Chosen depth | Winning L4 blend | Test quality/latency tradeoff |
| Full development | Best one or two | Fixed | Fixed | Select or reject reranking |
| Optional | Winner + hybrid dense | Fixed | Fixed | Run only if time remains |

**Alternatives considered:**

- **Semantic-only order:** simplest and useful as a diagnostic, but vulnerable to MS MARCO-to-shopping domain mismatch and hard-constraint violations.
- **Weighted raw-score addition:** easy but invalid because logits, BM25, RRF, and compatibility have unrelated scales. Rank fusion is the initial safe choice.
- **Learned linear ranker:** could learn weights from public targets, but 160 development sessions are too small for many features and make leakage/overfitting easy. Consider only in Task 11 with strict held-out evaluation.
- **Generative LLM reranking:** can reason about nuanced constraints, but adds latency, nondeterminism, cost, token accounting, and offline packaging. It is outside the initial three-day critical path.
- **ONNX/OpenVINO quantization:** useful if PyTorch CPU latency fails the gate. The official model repositories already include exported variants, but introducing another runtime should happen only after measuring the simple PyTorch path.
- **Rerank all 200 candidates:** maximizes the affected pool but may multiply latency without improving Top-10 metrics. Attempt only if depth microbenchmarks and ceiling analysis justify it.

**Planned files:**

- Create `starter/reranking.py`, `scripts/prepare_reranker.py`, and `tests/test_reranking.py`.
- Modify `starter/skills.py` to register `rerank_candidates`.
- Modify `starter/agent.py` to run reranking after retrieval and before policy with exact lexical fallback.
- Modify benchmark configuration, runner, reporting, and CLI for reranker variants, depths, batch sizes, pre/post ranks, and latency.
- Update `README.md`, `.gitignore`, and this plan with offline preparation commands, pinned revisions, measured results, and the selected default.

**Implementation result:**

- Task 7 candidate ceilings on 160 development sessions were Recall@20 `0.5125`, Recall@40 `0.66875`, Recall@60 `0.73125`, Recall@100 `0.80625`, and Recall@200 `0.8625`. Depth 60 was selected as the initial balance.
- MiniLM L4 is pinned at revision `777b2f369bc1c2f850df8bd367ed1654bda4497b`; its 76,667,004-byte Apache-2.0 safetensors file has SHA256 `acc066397c706f570eb373599355db29672bfb81f9a332237aa821edda2160d3`.
- MiniLM L6 is pinned at revision `233902d25c440f23af6f7d6e94d2946bac0bee0a`; its 90,866,412-byte Apache-2.0 safetensors file has SHA256 `a6e1fd85181a93a58bc33f65700f2ba34da3af2667f85cc57bcdf0f9f0092200`.
- L4 CPU microbenchmarks with batch 32 measured about `187ms`, `249ms`, and `415ms` at depths 40, 60, and 100. L6 measured `305ms`, `384ms`, and `646ms`. Both loaded successfully with network access disabled.
- On the deterministic 24-session pilot, the control scored MRR `0.281068` and TechnicalScore `0.477654`. L4 semantic-only scored `0.274223` and `0.475600`, so unguarded semantic ordering was rejected. Corrected L4 blend weight `0.25` scored `0.311343` and `0.485903`. L6 blend weight `0.25` scored `0.301091` and `0.486161`, but its negligible score advantage did not justify its higher latency and lower MRR.
- The selected development configuration is `multi_route_structured + dense_off + minilm_l4_blended + always_10`, rerank depth 60, batch size 32, semantic rank weight 0.25, retrieval rank weight 1.0.
- Full development results improved from Hit@10 `0.7000`, MRR `0.329673`, MTTC `6.175`, TechnicalScore `0.545402` to Hit@10 `0.7000`, MRR `0.343827`, MTTC `6.20625`, TechnicalScore `0.549023`. Mean turn latency was `380.28ms`, p95 `516.89ms`, mean reranker inference `250.84ms`, startup `8.51s`, with zero exceptions, warnings, or fallbacks. Artifact: `experiments/runs/20260828T140521Z_task9_full_l4_blend025`.
- The forced-offline official 200-session evaluator improved from Hit@10 `0.695`, MRR `0.327327`, MTTC `6.15`, TechnicalScore `0.542698` to Hit@10 `0.695`, MRR `0.338435`, MTTC `6.175`, TechnicalScore `0.545531`.
- All `82` tests pass; compilation and whitespace checks are clean; missing/corrupt models preserve the exact lexical ranking; no generative API or token usage is involved; and the lockbox remains untouched.

**Completion gate:** Reranking is deterministic, bounded, explainable, locally loadable without network access, and independently fallible; stale slots never enter model input; unscored tail order and structured evidence are preserved; all tests and the official contract pass; and the reranker becomes the default only if full-development MRR and TechnicalScore improve over `0.329673` and `0.545402` without a material Hit@10 or reliability regression. No lockbox sessions are used before Task 11.

## Task 10 — Implement adaptive orchestration

- [x] 10.1 Freeze the selected Task 9 configuration as the static control and add parity fixtures for buying, browsing, override, boundary, and late-turn scenarios.
- [x] 10.2 Add immutable planner contracts: `PlannerConfig`, `OrchestrationSignals`, `RetrievalPlan`, and `PlanDecision`.
- [x] 10.3 Implement `AdaptivePlanner.build_initial_plan(...)` using only active session state, current intent, event flags, and turn number.
- [x] 10.4 Add lightweight retrieval signals—candidate count, route contribution, score separation, and constraint-match coverage—and implement `refine_plan(...)` after first-stage lexical retrieval.
- [x] 10.5 Integrate the planner in `static_shadow` mode: compute and trace adaptive plans while executing the exact frozen Task 9 path.
- [x] 10.6 Allow lexical retrieval to accept per-call route weights, enabled routes, and candidate depths without mutating shared configuration.
- [x] 10.7 Allow the reranker to accept safe per-call enable/depth/weight overrides while preserving its exact lexical fallback.
- [x] 10.8 Activate and test precision mode for constrained Buying requests.
- [x] 10.9 Activate and test overload cutoff for vague Browsing requests; cut off expensive processing, not the contract-valid recommendations produced by the selected `always_10` policy unless a recommendation-count ablation proves better.
- [x] 10.10 Activate and test override recovery using only the newest state revision; broaden search when the new request invalidates the old candidate pool.
- [x] 10.11 Activate and test boundary/no-preference behavior so rejected attributes are not reintroduced or asked again.
- [x] 10.12 Activate and test late-turn coverage behavior with broader lexical and rerank depths; test dense rescue separately and keep it disabled unless it improves the combined score.
- [x] 10.13 Execute the registered skills in plan order from `Agent`, with a complete fallback to the frozen Task 9 plan if planning or a planned component fails.
- [x] 10.14 Add plan traces, unit/integration tests, benchmark dimensions, and controlled ablations that enable one adaptive rule at a time.
- [x] 10.15 Freeze the winning deterministic orchestration configuration; the optional LangGraph adapter was deferred because the score gate was not reached.

**Status:** Completed — `adaptive_cutoff` selected  
**Estimated time:** 3–4 hours for deterministic orchestration; up to 2 optional hours for the LangGraph adapter  
**Dependencies:** Tasks 6–9

**Outcome:** Each turn receives a small, explainable execution plan that changes retrieval effort and strategy according to the current active state. The Task 9 winner remains an immutable fallback. An optional framework adapter may visualize the same workflow but must not own the business rules.

### What changes in Task 10

Tasks 5–9 built independently testable capabilities, but `Agent` still invokes them using mostly static settings. Task 10 adds the control plane that decides which capabilities to call and how much work each should perform on this turn.

```text
understand turn -> update memory -> build initial plan
                                      |
                                      v
                               lexical retrieval
                                      |
                                      v
                          measure retrieval signals
                                      |
                                      v
                                refine the plan
                              /        |        \
                         dense?    rerank?    cutoff?
                              \        |        /
                                      v
                       recommendation + clarification
                                      |
                                      v
                         validate response and trace plan

Any planner/component failure -> frozen Task 9 execution plan
```

This is **two-phase planning**:

1. The initial plan uses facts known before retrieval: route, active slots, override/no-preference events, turn number, and prior session state.
2. The refined plan uses facts learned from lexical retrieval: whether the pool is saturated, whether several routes agree, whether constraints are represented, and whether leading candidates are separated clearly enough to justify reranking.

The planner is deterministic Python. It does not make an LLM call and it must not read the full raw transcript. It consumes the distilled active state created in Task 4, which prevents superseded constraints from leaking back into retrieval.

### Knowledge required before implementation

- **Orchestration:** choosing the next operations and their parameters; it is separate from implementing retrieval or reranking.
- **Control plane versus data plane:** the planner creates a plan; existing skills perform the searches, scoring, and response generation.
- **Immutable per-turn plan:** create a new plan for every turn and pass it to components. Never modify a global retriever/reranker configuration because that can leak decisions between sessions.
- **Shadow mode:** produce and log a proposed adaptive plan while the static Task 9 plan still controls output. This verifies integration and observability before behavior changes.
- **Dynamic context programming:** compile the active conversational state into concrete execution settings. This is broader than inserting conversation history into a prompt.
- **Overload cutoff:** stop unnecessary expensive stages when a vague request produces a large, weakly differentiated pool. It does not mean returning an invalid or empty response.
- **Fallback:** if planning or an optional stage fails, run the known-good Task 9 configuration and preserve the API contract.
- **Ablation:** change one rule at a time so a score movement can be attributed to that rule.

### Planner contracts

Create `starter/orchestration.py` with small typed, frozen data structures. Exact field names can follow existing project conventions, but the minimum information should be equivalent to:

```python
@dataclass(frozen=True)
class OrchestrationSignals:
    route: str
    turn_number: int
    active_slot_count: int
    has_hard_constraints: bool
    is_override: bool
    has_no_preference: bool
    candidate_count: int | None = None
    route_count: int | None = None
    score_margin: float | None = None
    constraint_coverage: float | None = None


@dataclass(frozen=True)
class RetrievalPlan:
    version: str
    mode: str
    reasons: tuple[str, ...]
    skill_order: tuple[str, ...]
    lexical_route_weights: Mapping[str, float]
    lexical_depth: int
    fusion_depth: int
    dense_enabled: bool
    reranker_enabled: bool
    rerank_depth: int
    semantic_rank_weight: float
    recommendation_policy: str
    clarification_priority: str | None
```

`PlanDecision` should hold the initial plan, optional refined plan, changed fields, and fallback reason. This makes every runtime decision visible in a benchmark trace without coupling the benchmark to planner internals.

### Initial scenario modes

Keep the first rules deliberately small. The numbers below start from the Task 9 winner and are hypotheses to benchmark, not permanent defaults.

| Mode | Trigger | Initial behavior | Purpose |
|---|---|---|---|
| `precision` | Buying plus reliable hard constraints | Structured multi-route lexical retrieval; dense off; MiniLM L4 rerank depth 60 and semantic weight 0.25; `always_10` | Preserve the proven Task 9 precision path |
| `exploration` | Browsing with useful scenario/category evidence | Emphasize category, feature, and current-turn routes; use moderate depth; rerank only when lexical signals justify it | Add diversity without discarding relevant categories |
| `overload_cutoff` | Very vague early browsing plus a saturated, weakly separated pool | Skip dense and possibly semantic reranking; generate the best clarification; retain the selected recommendation policy until separately disproved | Reduce unnecessary cost and guide convergence |
| `override_recovery` | Intent/category/constraint override | Search from the newest state revision only; allow products shown under the old revision to appear again; use broad lexical recovery and reranking | Prevent stale-slot contamination |
| `boundary_broad` | Explicit no-preference/boundary response | Broaden the rejected attribute while preserving all other active constraints; never ask it again in the same revision | Respect user-declared boundaries |
| `late_coverage` | Turn 8+ or repeated retrieval miss/weakness | Increase lexical/fusion/rerank depth; optionally test dense rescue as an isolated variant | Prefer recall before the 10-turn termination limit |

The recommendation-count policy is **not silently changed in this task**. `always_10` is the frozen control because it beat the implemented dynamic variants after Task 7. The plan may trace a proposed count, but a different count becomes active only if a named ablation improves TechnicalScore. A vague-query cutoff initially means avoiding wasteful retrieval/reranking and asking a useful question while still returning the control policy's recommendations.

### Sequential implementation details

#### 10.1 — Freeze control and parity fixtures

Record the current selected settings in one read-only planner constant or constructor helper: `multi_route_structured`, `dense_off`, `minilm_l4_blended`, rerank depth `60`, batch size `32`, semantic rank weight `0.25`, and `always_10`. Add representative fixtures for all five scenario families. Capture the current ASIN order and response shape for each fixture before integrating adaptive behavior.

**Gate:** Direct execution through the frozen plan reproduces Task 9 outputs exactly.

#### 10.2 — Add contracts and deterministic planner

Implement pure functions or a small `AdaptivePlanner` class. Plan construction must be side-effect free: the same signals and configuration always produce the same plan. Validate non-negative weights/depths and known skill names at construction time.

**Gate:** Unit tests cover default, buying, browsing, override, boundary, late-turn, invalid-config, and determinism cases.

#### 10.3 — Add post-retrieval refinement

Derive only cheap signals from the ranked candidates already available. Do not run an extra model just to decide whether to run the model. Use stable measurements such as candidate count, number of contributing routes, structured constraint matches, and a normalized top-score margin. Store thresholds in `PlannerConfig`, not scattered `if` statements.

**Gate:** Fixed candidate fixtures always produce the expected refined plan, including low-margin and saturated-pool cases.

#### 10.4 — Integrate shadow mode

Insert planning after state update and refinement after lexical retrieval, but continue executing the frozen plan. Add trace fields for mode, reasons, proposed settings, executed settings, changed fields, and fallback. Run the full development benchmark and verify identical recommendation lists and metrics to Task 9.

**Gate:** Shadow-mode output parity is exact; errors and planner fallbacks are zero; latency overhead is small and recorded.

#### 10.5 — Make skills accept per-call settings

Extend lexical retrieval and reranking with optional typed override arguments. Default arguments must preserve all current behavior. Never mutate registry entries or shared dataclass instances. Dense retrieval remains available but disabled by default.

**Gate:** Existing tests remain green, concurrent/sequential sessions cannot influence each other, and omitting overrides preserves exact Task 9 order.

#### 10.6 — Activate one scenario rule at a time

Enable `precision`, `exploration`, cutoff, override, boundary, and late coverage as separate named benchmark variants. Do not switch on the full rule set first. After every rule, compare full metrics plus its relevant scenario slice against the static control.

**Gate:** A rule enters the combined variant only when it improves its target slice without a material overall Hit@10, reliability, or latency regression.

#### 10.7 — Integrate the plan with the registry and Agent

`Agent` should request the plan and execute registered skills in its declared order. Keep orchestration shallow: the planner chooses existing skills, while each skill continues to own its implementation. Catch planner validation/execution errors at this boundary and substitute the frozen Task 9 plan.

**Gate:** Every response remains schema-valid and every optional skill can fail independently without changing the lexical fallback order.

#### 10.8 — Benchmark and freeze the winner

Run the following controlled sequence:

1. Frozen Task 9 static control.
2. Static shadow-mode parity.
3. Adaptive rerank depth only.
4. Browsing overload cutoff only.
5. Override and boundary recovery only.
6. Late-turn coverage only.
7. Combined rules that passed their individual gates.
8. Optional recommendation-count variants, still isolated from route changes.
9. Optional dense rescue, still isolated because Task 8 selected `dense_off`.

For each run report Hit@10, MRR, MTTC, TechnicalScore, scenario slices, plan-mode counts, mean/p95 turn latency, reranker calls avoided, mean rerank depth, fallbacks, warnings, and exceptions.

**Selection rule:** Prefer the highest repeatable development TechnicalScore. Do not accept a material Hit@10 regression for a small latency gain. The current controls are development TechnicalScore `0.549023` and official public TechnicalScore `0.545531`. Keep the lockbox untouched until Task 11. If no adaptive variant beats the static control, keep Task 9 as the execution default and retain shadow-mode plans/traces for the architecture demonstration; do not claim a score improvement.

#### 10.9 — Optional thin LangGraph adapter

Attempt this only after deterministic orchestration is complete and frozen. Map the existing stages to graph nodes and use conditional edges for optional dense/rerank paths. Nodes call the same planner and registered skills; no business rules are duplicated inside the graph. Keep direct Python execution as the official fallback and avoid adding the dependency to the required offline path unless packaging is verified.

**Gate:** Direct and graph executions produce contract-equivalent outputs for every parity fixture, and the adapter fits within the two-hour limit. Otherwise defer it to the post-hackathon plan.

### Files to create or modify

| File | Change |
|---|---|
| `starter/orchestration.py` | New immutable contracts, planner configuration, static fallback, initial plan, and refinement logic |
| `starter/agent.py` | Request/refine a plan, execute its skill order, and apply the frozen fallback |
| `starter/retrieval.py` | Accept validated per-call route/depth overrides without shared-state mutation |
| `starter/reranking.py` | Accept validated per-call enable/depth/weight overrides and preserve exact fallback |
| `starter/skills.py` | Pass typed plan inputs through existing registered skill boundaries only where needed |
| `benchmarking/models.py`, `benchmarking/runner.py`, `benchmarking/reporting.py`, `scripts/benchmark.py` | Add orchestration variants, trace summaries, and per-mode efficiency diagnostics |
| `tests/test_orchestration.py` | New pure planner, refinement, shadow parity, and fallback tests |
| Existing agent/retrieval/reranking tests | Add default-parity and per-call-override cases |
| `starter/langgraph_adapter.py` | Optional only after the deterministic score gate |
| `README.md` | Document selected plan modes, benchmark command, and optional adapter |

### Alternatives considered

- **One large conditional block inside `Agent`:** slightly faster to write, but harder to unit-test, trace, ablate, and reuse from an optional graph. A small planner module is still simple and keeps decision logic together.
- **LLM planner:** not selected. It adds nondeterminism, latency, credentials, and failure modes to decisions that can be expressed from structured signals.
- **Make LangGraph mandatory:** not selected for the scored path. The project already has a small deterministic pipeline, and framework migration should not threaten offline reproducibility.
- **Always run lexical, dense, and reranking in parallel:** not selected because Task 8 showed dense retrieval did not win, while always invoking every route prevents meaningful efficiency adaptation.
- **Build plans from the full transcript:** not selected because stale/superseded statements could bypass the state machine. Plan only from the active distilled state and explicit event flags.
- **Learn the policy now:** deferred to Task 11's conditional bandit experiment. With only 200 public sessions, deterministic rules are easier to diagnose and less likely to overfit.

**Completion gate:** The full test suite and official API contract pass; shadow mode exactly reproduces Task 9; logs show deterministic and meaningfully different plans for vague browsing, constrained buying, override, boundary, and late-turn states; no state/configuration leaks between sessions; every failure falls back to the frozen Task 9 ranking; the selected execution default is justified by controlled full-development results; and the lockbox remains unused. If the adapter is attempted, graph and direct execution must produce contract-equivalent outputs on the same fixtures.

### Task 10 implementation result

- The deterministic two-phase planner, immutable plan contracts, per-call lexical/reranker controls, frozen fallback, shadow mode, plan traces, benchmark CLI variants, and orchestration diagnostics are implemented.
- The static and `static_shadow` 12-session parity runs produced identical Hit@10 `0.666667`, MRR `0.484259`, MTTC `6.833333`, and TechnicalScore `0.561945`; shadow mode executed 78 static plans with zero fallbacks.
- `adaptive_rerank` and `adaptive_recovery` were rejected in pilots because they reduced MRR and increased latency. Their named variants remain available for reproducible diagnostics.
- `adaptive_cutoff` preserved the pilot score while avoiding five reranker calls. On the full 160-session development split it produced Hit@10 `0.700000`, MRR `0.349080`, MTTC `6.225000`, and TechnicalScore `0.550224`, compared with the Task 9 development control `0.700000`, `0.343827`, `6.206250`, and `0.549023`.
- The selected variant avoided semantic reranking on 59 of 948 turns. Mean/p95 turn latency improved from the Task 9 measurement of approximately `380/517 ms` to `347/483 ms`, with zero exceptions, warnings, or planner fallbacks.
- `always_10`, `dense_off`, `multi_route_structured`, and MiniLM L4 depth 60/semantic weight 0.25 remain the normal-turn defaults. Only the evidence-backed overload cutoff changes runtime execution.
- Development artifact: `experiments/runs/20260828T153101Z_task10_cutoff_development`. The stratified lockbox was not run. The optional LangGraph adapter was skipped because the `TechnicalScore >= 0.78` gate was not reached and it would not improve the scored path.

## Task 11 — Tune with controlled experiments and ablations

- [x] 11.1 Freeze Task 10's `adaptive_cutoff` result as the control and keep all runtime code independent of public-session labels, ground truth, sample IDs, and simulator-only intent cards.
- [x] 11.2 Add deterministic multi-query dense contracts for identity, active constraints, scenario/need, and optional profile-prior views. Compile only active session values so superseded intent never reaches retrieval.
- [x] 11.3 Add structured dense-rescue fusion: admit dense-only candidates into the reranker head only when they do not contradict active hard constraints. Preserve the lexical head and tail order.
- [x] 11.4 Run isolated 12-session pilots for multi-query retrieval on the original index and structured dense rescue. Reject changes that regress the control before expensive evaluation.
- [x] 11.5 Build catalog-only field-aware product embeddings for identity, attributes, and needs/scenario views. Do not use public queries or target labels to create these documents.
- [x] 11.6 Pilot field-aware retrieval without profile priors, then add profile priors at low weight only if the base fielded path is stable. Treat profile data as preference evidence, never a hard filter.
- [x] 11.7 Compare the surviving configuration with Task 10 on the full 160-session development set and deterministic scenario/fold slices. Tune only query-view weights or rescue depth, not both at once.
- [x] 11.8 Freeze the highest repeatable configuration only if it improves TechnicalScore without a material Hit@10, reliability, or latency regression. Otherwise retain Task 10.
- [x] 11.9 Run the reserved 40-session stratified lockbox exactly once after every implementation and tuning decision is frozen; do not tune from its result.
- [x] 11.10 Record artifacts, results, selected defaults, rejected alternatives, and limitations in this plan.
- [x] 11.11 Skip the conditional contextual-bandit experiment because the required `TechnicalScore >= 0.78` gate was not reached.

**Status:** Completed — Task 10 `dense_off` configuration retained  
**Estimated time:** 3–4 hours  
**Dependencies:** Task 10

**Outcome:** Select a configuration that generalizes beyond repeatedly inspected public examples.

**Knowledge required:** Overfitting occurs when choices match the 200 public targets but fail on unseen private sessions. An ablation changes one component at a time.

**How:** Start from Task 10 and change one retrieval component at a time. First test multi-query retrieval and hard-constraint-verified dense rescue. Then correct query/document mismatch with three catalog-only product views: identity (`title/category/brand`), attributes (`materials/colors/features/details/price`), and needs (`features/description/use-oriented language`). Search each view with its matching state-derived query and combine ranks with deterministic weighted RRF. Profile tags and summary form a separate low-weight semantic route; they may boost compatible products but may never exclude a candidate or override current intent. Optimize combined TechnicalScore while checking scenario and deterministic fold slices. If the score gate is already met, model the clarification attribute and recommendation count as bandit actions using route, turn, active slots, candidate-pool size, and score margin as context. Use the official TechnicalScore components as reward and compare against the frozen heuristic on held-out sessions.

**Alternatives:** Manual search is sufficient. Skip the bandit if data is too sparse or held-out score does not improve; the full policy-learning lifecycle belongs in the post-hackathon plan.

**Completion gate:** A frozen configuration has a written evidence-based justification and acceptable lockbox behavior. A bandit may be claimed only if it is actually trained from reward feedback and beats the heuristic on held-out TechnicalScore.

### Task 11 interim results

- Original-index multi-query pilot (`hybrid_dense_multi`, 12 development sessions): Hit@10 `0.666667`, MRR `0.387500`, MTTC `7.166667`, TechnicalScore `0.526250`. It regressed the Task 10 static pilot because specialized queries were matched against one broad product representation; this variant is rejected.
- Structured single-query rescue pilot (`hybrid_dense_rescue`, 12 development sessions): Hit@10 `0.666667`, MRR `0.484259`, MTTC `6.833333`, TechnicalScore `0.561945`, identical to the pilot control. It raised combined route recall from `0.833333` to `0.916667` through one dense-only addition, with a small latency increase, so rescue is retained only as an enabling mechanism for the field-aware pilot.
- Field-aware product documents and profile-aware query support are implemented behind named experimental variants. Three catalog-only 50,000-product caches were built locally with the pinned BGE revision and validated catalog/ASIN/file checksums; no public query, target label, or simulator-only field was used.
- Field-aware pilot (`hybrid_dense_fielded`, 12 development sessions): Hit@10 `0.666667`, MRR `0.484259`, MTTC `6.833333`, TechnicalScore `0.561945`. The scenario view reached Recall@200 `0.583333` versus `0.500000` for original-index multi-query, and dense still added one lexical miss, but final score was unchanged and mean turn latency rose to about `437ms`.
- Low-weight profile pilot (`hybrid_dense_fielded_profile`, same 12 sessions): identical official metrics, while the profile-only route found zero targets at 200. Profile retrieval remains implemented and correctly subordinate to current intent, but is rejected from the full comparison because it supplied no evidence of value.
- Full field-aware development comparison (`hybrid_dense_fielded` + `adaptive_cutoff`, 160 sessions): Hit@10 `0.700000`, MRR `0.347875`, MTTC `6.212500`, TechnicalScore `0.550113`, mean/p95 turn latency about `449/637ms`, zero errors. Route-union Recall@200 reached `0.943750` and dense uniquely added targets for `0.031250` of sessions, but this did not improve final Top-10 ranking. Compared with Task 10 (`0.700000`, `0.349080`, `6.225000`, `0.550224`, about `347/483ms`), score and MRR regressed slightly while latency increased materially. Reject field-aware dense as the default and retain Task 10's `dense_off` configuration.
- Frozen one-time lockbox (`dense_off` + MiniLM L4 + `adaptive_cutoff`, 40 sessions): Hit@10 `0.675000`, MRR `0.298115`, MTTC `6.050000`, TechnicalScore `0.525934`, candidate Recall@200 `0.925000`, mean/p95 latency about `391/534ms`, and zero warnings, exceptions, or fallbacks. The lower score is recorded as a generalization warning; no configuration was changed after observing it.
- Final Task 11 default: Task 10's stateful multi-route structured lexical retrieval, MiniLM L4 blended reranking at depth 60/weight 0.25, deterministic `adaptive_cutoff`, `always_10`, and `dense_off`. Experimental dense/profile variants remain reproducible ablations and automatic lexical fallback remains available, but their additional runtime is not paid on the scored path.

**Artifacts:** `experiments/runs/20260829T082027Z_task11_multi_query_pilot`, `experiments/runs/20260829T082113Z_task11_rescue_pilot`, `experiments/runs/20260829T083828Z_task11_fielded_pilot`, `experiments/runs/20260829T083919Z_task11_fielded_profile_pilot`, `experiments/runs/20260829T084027Z_task11_fielded_development`, and `experiments/runs/20260829T084814Z_task11_frozen_lockbox`.

## Task 11B — Post-lockbox reranker safety research

- [x] Preserve Task 11's frozen default and prohibit additional lockbox evaluation.
- [x] Implement explicit hard/soft query formatting and concise field-aware product documents.
- [x] Implement bounded structured compatibility, hard-contradiction penalties, and auditable trace contributions.
- [x] Implement deterministic maximum-rank-movement guarding.
- [x] Preserve the first-turn Buying/Browsing route as a runtime-only session-origin signal and test route-aware context selection.
- [x] Run one-variable 24-session development pilots and advance only pilot winners.
- [x] Run full development comparisons for the route-aware and bounded winners; retain the frozen submission default because no untouched validation set remains.

**Status:** Completed — `minilm_l4_bounded` retained as an experimental variant; frozen default unchanged  
**Evaluation boundary:** This work occurred after the one-time lockbox. It uses only the development split, never reruns the lockbox, and cannot replace the submission default without new untouched validation data.

### Reranker experiment results

| Variant | Samples | Hit@10 | MRR | MTTC | TechnicalScore | Decision |
|---|---:|---:|---:|---:|---:|---|
| Existing blended control | 24 | 0.625000 | 0.311343 | 7.000000 | 0.485903 | Pilot control |
| Field-aware context | 24 | 0.625000 | 0.254861 | 6.833333 | 0.472292 | Reject; Buying MRR collapsed |
| Fielded + constraints | 24 | 0.625000 | 0.249537 | 6.958333 | 0.468194 | Reject |
| Fielded + constraints + movement guard | 24 | 0.625000 | 0.241832 | 6.958333 | 0.465883 | Reject |
| Initial-route-aware context | 24 | 0.625000 | 0.305787 | 6.875000 | 0.486736 | Pilot winner; advanced |
| Legacy context + constraints | 24 | 0.625000 | 0.260185 | 6.958333 | 0.471389 | Reject; structured evidence was already represented in retrieval rank |
| Legacy context + movement guard | 24 | 0.625000 | 0.306481 | 6.875000 | 0.486944 | Best pilot; advanced |
| Initial-route-aware context | 160 | 0.693750 | 0.336446 | 6.175000 | 0.544309 | Reject; Hit@10 and Boundary regressed |
| Legacy context + maximum movement 8 | 160 | 0.700000 | 0.350322 | 6.206250 | 0.550972 | Promising development-only result |

The bounded variant improved the Task 10 development control (`0.550224`) by `0.000748`, preserved Hit@10, increased MRR by `0.001242`, improved MTTC by `0.01875`, and reduced target-demotion turns from `100` to `95`. The change adds no model calls and only performs a small deterministic in-memory bounded sort. However, the gain is too small to claim generalization without a fresh validation set. Fielded documents remain useful research infrastructure, but the generic MS MARCO cross-encoder handled their required/preferred phrasing poorly for this catalog. Direct compatibility reweighting also double-counted evidence already embedded in structured retrieval order.

**Artifacts:** `experiments/runs/20260829T110137Z_rerank_addendum_control`, `experiments/runs/20260829T110252Z_rerank_addendum_fielded`, `experiments/runs/20260829T110410Z_rerank_addendum_constraint`, `experiments/runs/20260829T110520Z_rerank_addendum_guarded`, `experiments/runs/20260829T110916Z_rerank_addendum_origin_aware`, `experiments/runs/20260829T111722Z_rerank_addendum_constraint_legacy`, `experiments/runs/20260829T111836Z_rerank_addendum_bounded`, `experiments/runs/20260829T111051Z_rerank_addendum_origin_aware_development`, and `experiments/runs/20260829T111950Z_rerank_addendum_bounded_development`.

## Task 12 — Add reliability, offline fallback, and performance controls

- [x] Validate every output against the contract.
- [x] Handle empty retrieval and component failures.
- [x] Provide dense and reranker fallbacks.
- [x] Measure startup, mean/p95 latency, memory, model size, tokens, and cost.
- [x] Confirm the full development evaluator-compatible run finishes with network access disabled; preserve the consumed lockbox.
- [x] Verify every registered skill can fail independently without invalidating the response contract.

**Status:** Completed  
**Estimated time:** 2 hours  
**Dependencies:** Task 11

**Outcome:** A system and Agent harness that remain valid under organizer restrictions.

**Knowledge required:** A reliable weaker fallback is better than a high-scoring path that can time out or fail to load.

**How:** Catch component failures, fall back through semantic → hybrid lexical → category-popularity retrieval, and validate ASIN uniqueness and membership.

**Alternatives:** Reduce rerank depth or use MiniLM L4 if latency is poor.

**Completion gate:** The full development evaluator-compatible run finishes with forced-offline models, zero contract violations or unhandled exceptions, measured resource usage, and independently tested fallbacks. The consumed lockbox is not rerun.

### Task 12 implementation result

- Added a final `ResponseGuard` that guarantees string message, allowed clarification attribute, unique catalog-valid ASINs, `top_k`/100-item limits, and valid zero-token usage. It records guard corrections as warnings and is inactive on valid normal responses.
- Extended the fallback chain from structured retrieval to single BM25, category-local or global popularity, and finally a contract-valid empty result. Each transition is independently traced.
- Added failure-injection coverage for understanding, memory, lexical retrieval, dense retrieval, semantic reranking, planning, policy, missing model artifacts, empty retrieval, and total retrieval failure. Every path returns a valid response.
- Added benchmark measurements for wall runtime, startup time, initial/startup/final peak RSS, startup/runtime peak growth, selected artifact sizes, token usage, external calls, and estimated external cost.
- Avoided compiling unused fielded reranker documents on the frozen legacy path. The 12-session offline smoke peak fell from about `1.60GB` to `1.45GB`, and startup fell from `9.41s` to `8.89s`, with identical metrics.
- Final forced-offline 160-session development run: Hit@10 `0.700000`, MRR `0.349080`, MTTC `6.225000`, TechnicalScore `0.550224`; 948 turns; zero exceptions, warning turns, fallbacks, guard activations, tokens, external calls, or external cost.
- Final performance: startup `8.27s`, mean/p95 turn latency `347/477ms`, wall runtime `337.9s`, peak process RSS `1.76GB`, catalog `57.7MB`, reranker bundle `73.8MB`, total required artifacts `131.5MB`.
- The local benchmark reuses the official simulator/evaluation functions and previously passed exact official-metric parity. It was used for the full development run so the already-consumed 40-session lockbox was not rerun.

**Artifacts:** `experiments/runs/20260830T021018Z_task12_offline_smoke`, `experiments/runs/20260830T023121Z_task12_offline_smoke_optimized`, and `experiments/runs/20260830T023213Z_task12_offline_development`.

## Task 13 — Final evaluation, packaging, report, and demo

- [x] Run tests and final evaluator.
- [x] Run the frozen lockbox once.
- [x] Produce submission source, requirements, assets, and README.
- [x] Document models, latency, memory, token use, cost, fallbacks, and limitations.
- [x] Prepare one multi-turn demonstration.

**Status:** Completed  
**Estimated time:** 3–4 hours  
**Dependencies:** Task 12

**Outcome:** A reproducible submission another machine can run from written instructions.

**Knowledge required:** Judges need reproducibility and transparent engineering tradeoffs in addition to the local score.

**How:** Package a thin `Agent` entry point plus internal modules and local assets. Demonstrate vague browsing, clarification, accumulation, override invalidation, and convergence.

**Alternatives:** If model assets are too large, document an installation download and preserve a completely offline lexical fallback.

**Completion gate:** A clean environment can install and run the official evaluator using only the submission instructions.

**Implementation summary:**

- Added a thin official `agent:Agent` adapter that resolves the bundled model independently of the working directory while accepting the organizer-provided catalog path.
- Added a deterministic allowlist-based packager. It includes the required `starter` modules, pinned requirements, judge-facing README/report/demo, and only the selected MiniLM-L4 artifacts. It excludes the catalog, public labels, evaluator, experiments, caches, secrets, BGE dense model, and MiniLM-L6 model.
- Added `MANIFEST.json` with every included file's size and SHA256, the catalog checksum, Python version, offline disclosure, entry point, and frozen configuration. Two consecutive builds produced byte-identical archives.
- Added an archive checker that rejects unsafe or disallowed paths, verifies every manifest hash, validates the frozen catalog checksum, extracts to a temporary directory, loads the bundled model with networking forced off, and checks three stateful Agent responses against the contract and catalog.
- Verified the written setup from a brand-new Python 3.12.14 virtual environment: all 40 pinned packages installed from `requirements.txt`, then the extracted archive completed its six-turn demo with model access forced offline.
- Added a six-turn label-free demonstration covering vague Browsing, proactive clarification, a Boundary no-preference response, accumulated category/budget constraints, explicit Intent Override, stale category/audience/budget replacement, search-revision increment, and convergence. It returned ten valid recommendations on every turn with no fallback.
- Final test suite: 117 tests passed. Final forced-offline 160-session development verification exactly reproduced Hit@10 `0.700000`, MRR `0.349080`, MTTC `6.225000`, TechnicalScore `0.550224`; 948 turns; zero exceptions, warning turns, fallbacks, tokens, external calls, or cost.
- Final measured performance: startup `8.21s`, mean/p95 turn latency `349/481ms`, wall runtime `339.9s`, peak RSS `1.78GB`, and selected catalog/model artifacts `131.5MB`.
- The one-time 40-session lockbox requirement was completed in Task 11 (TechnicalScore `0.525934`). It was deliberately not rerun during Tasks 12 or 13.

**Submission artifact:** `dist/techjam-shopping-agent.zip`, 70,284,156 bytes, SHA256 `65ebdd0df2ea2f692fe882d137ea05fc8fc58da367a1c8eea0bdad7aac314076`.

**Evaluation artifact:** `experiments/runs/20260830T024653Z_task13_final_submission`.

---

## Decision log

| Date | Decision | Reason | Revisit when |
|---|---|---|---|
| 2026-08-27 | Use confidence-aware dynamic recommendation count instead of always returning 10 | Early low-rank hits can lock poor MRR; over-general queries require retrieval cutoff | After Task 6 ablations |
| 2026-08-27 | Invalidate only superseded intent slots by default | Preserves valid accumulated information while removing retrieval contamination | Parser shows ambiguous override scope |
| 2026-08-27 | Clear/soften shown-product penalties on override | Pre-override appearances do not count and the target must be allowed to reappear | Evaluator protocol changes |
| 2026-08-27 | Keep official path offline-first | Final scoring may disable network access | Organizer explicitly guarantees network |
| 2026-08-27 | Add a lightweight typed skill registry during the hackathon | Directly improves modularity, harness traces, testing, and role alignment with low implementation risk | Skill abstraction adds measurable latency or complexity |
| 2026-08-27 | Make LangGraph a two-hour conditional adapter | Demonstrates framework knowledge without coupling the scoring path to it | Day 2 score gate is missed |
| 2026-08-27 | Make the contextual bandit a three-hour conditional experiment | It is metric-aligned innovation but carries tuning and overfitting risk | Day 2 score gate is missed or held-out gain is absent |
| 2026-08-27 | Defer production service, multi-agent critic, and merchant analyst | These improve role alignment but do not justify competition risk in the three-day core | Hackathon submission is frozen |
| 2026-08-28 | Select MiniLM L4 depth 60 with retrieval/semantic rank weights 1.0/0.25 | It improved development and official MRR/TechnicalScore with unchanged Hit@10 and lower latency than L6 | Task 11 held-out tuning or Task 12 latency work changes the tradeoff |
| 2026-08-28 | Select deterministic `adaptive_cutoff` orchestration | It improved development TechnicalScore and MRR while skipping 59 unhelpful reranker calls with unchanged Hit@10 | Task 11 held-out evidence shows regression |
| 2026-08-28 | Defer the optional LangGraph adapter | The required score gate was not reached; direct Python orchestration is complete, offline-safe, and score-relevant | Core submission is frozen with time remaining |
| 2026-08-29 | Retain `dense_off` after Task 11 | Field-aware dense added Recall@200 coverage but slightly reduced full-development score/MRR and increased latency; profile retrieval added no pilot target recall | A future reranker can reliably convert dense-only candidates into Top-10 gains on unseen data |
| 2026-08-29 | Freeze before and do not tune from the one-time lockbox | The 40-session score was lower than development, demonstrating the intended generalization check | Never during this submission; use only new training/development data in a future iteration |
| 2026-08-29 | Keep bounded reranking experimental after a small development gain | Maximum movement 8 improved development TechnicalScore to `0.550972`, but the lockbox was already consumed and no untouched validation set remains | Fresh labeled sessions reproduce the gain without scenario regression |

## Experiment log

| Experiment | Configuration | Hit@10 | MRR | MTTC | Score | Decision |
|---|---|---:|---:|---:|---:|---|
| Official baseline | Stateless starter BM25 | 0.125 | 0.068034 | 9.81 | 0.10671 | Replace with stateful pipeline |
| Benchmark parity | New participant-owned harness, all 200 sessions | 0.125 | 0.068034 | 9.81 | 0.10671 | Exact parity confirmed; candidate recall remains unmeasured until the Agent emits traces |
| Diagnostic only | Stateful cumulative lexical retrieval plus clarification | 0.84 | 0.54005 | 3.875 | 0.724515 | Strong evidence for state/question policy; reproduce properly in Tasks 4–7 |
| Task 9 control | Task 7 lexical/structured, 160 development sessions | 0.7000 | 0.329673 | 6.175 | 0.545402 | Frozen reranker control |
| Task 9 selected | MiniLM L4 blended, depth 60, weight 0.25, 160 development sessions | 0.7000 | 0.343827 | 6.20625 | 0.549023 | Select as default |
| Task 9 official | Selected reranker, all 200 public sessions, forced offline | 0.695 | 0.338435 | 6.175 | 0.545531 | Official submission path verified |
| Task 10 selected | Task 9 pipeline plus overload cutoff, 160 development sessions | 0.7000 | 0.349080 | 6.225 | 0.550224 | Select `adaptive_cutoff`; 59 reranker calls avoided |
| Task 11 fielded dense | Three catalog-only BGE views, verified rescue, adaptive cutoff, 160 development sessions | 0.7000 | 0.347875 | 6.2125 | 0.550113 | Reject: slight score/MRR regression and about 102ms higher mean latency |
| Task 11 lockbox | Frozen Task 10 winner, reserved 40 sessions, forced offline | 0.6750 | 0.298115 | 6.0500 | 0.525934 | Record only; no post-lockbox tuning |
| Task 11B bounded reranker | Legacy MiniLM blend with maximum rank movement 8, 160 development sessions | 0.7000 | 0.350322 | 6.20625 | 0.550972 | Promising research result; do not replace frozen default without fresh validation |

## Parking lot — optional after the core is stable

- [ ] Expected-information-gain question selection.
- [ ] Catalog-derived weak supervision and hard-negative mining.
- [ ] Learned linear fusion model.
- [ ] MMR browsing diversity.
- [ ] Natural recommendation explanations.
- [ ] Complete items in `POST_HACKATHON_ROLE_ALIGNMENT_PLAN.md` after freezing the hackathon submission.
