# Post-Hackathon TikTok Shop Role-Alignment Plan

Last updated: 2026-08-27

This plan begins only after the official hackathon submission is frozen. Its purpose is to turn the evaluated shopping-search MVP into a production-oriented Agent AI portfolio project aligned with the attached TikTok Shop internship description.

The hackathon implementation remains the immutable performance baseline. Post-hackathon services consume its public interfaces rather than rewriting the working retrieval core without evidence.

## How to use this plan

- Complete the phases sequentially unless a dependency explicitly allows parallel work.
- Maintain measured before/after results for latency, quality, reliability, and business usefulness.
- Do not describe an item as multi-agent, reinforcement learning, production deployment, or prompt tuning until that capability is genuinely implemented and evaluated.
- Resume claims must use measured results and link to reproducible artifacts.

## Target role-coverage progression

| Milestone | Estimated technical-job coverage |
|---|---:|
| Completed hackathon architecture | 66–70% |
| + Production harness, API, graph, and skills | 77–82% |
| + Multi-agent critic, learned policy, and merchant analyst | 88–92% |

These percentages are an evidence-planning rubric, not an employer-provided score. Degree status, availability, communication, and collaboration must be demonstrated separately in the resume and interview.

## Post-hackathon architecture

```text
Clients / Demo / Evaluation Harness
              |
              v
FastAPI Agent Gateway
 auth • schemas • rate limits • health • readiness
              |
              v
Agent Harness and Observability
 traces • replay • prompt/config versions • cost • latency • fallbacks
              |
              v
LangGraph Supervisor
              |
     +--------+-------------------+
     |                            |
     v                            v
Shopping Planner Agent       Merchant Analyst Agent
     |                            |
     v                            +-- failure clustering
Typed Skill Registry              +-- catalog gap analysis
     |                            +-- discoverability reports
     +-- memory/context            `-- operational recommendations
     +-- lexical/dense search
     +-- metadata constraints
     +-- semantic reranking
     +-- clarification policy
     `-- explanation generation
     |
     v
Constraint Critic Agent
 verifies evidence • detects conflicts • requests rerank/replan
     |
     v
Recommendation Response

Telemetry and simulator episodes
              |
              v
Offline Policy Learning
 contextual bandit / RL evaluation • policy registry • rollback

Shared data plane
 catalog knowledge base • session memory • experiment store • model assets
```

## Current status

| Phase | Status | Primary job-description evidence |
|---|---|---|
| PH0. Freeze and document baseline | Pending | Requirement analysis and iteration discipline |
| PH1. Production Agent gateway | Pending | Development-to-launch lifecycle |
| PH2. Full LangGraph workflow | Pending | Mainstream Agent framework and orchestration |
| PH3. Skills and prompt operations | Pending | Skill development, prompt tuning, harness |
| PH4. Multi-agent constraint critic | Pending | Multi-agent collaboration |
| PH5. Merchant Search Quality Analyst | Pending | Merchant operations and decision support |
| PH6. Offline policy learning | Pending | Reinforcement learning and self-improvement |
| PH7. Production evaluation and security | Pending | Reliable platform services |
| PH8. Portfolio and resume evidence | Pending | Communication and concise technical storytelling |

---

## PH0 — Freeze and document the hackathon baseline

- [ ] Tag or branch the final hackathon implementation.
- [ ] Preserve exact dependencies, models, assets, configuration, and evaluator output.
- [ ] Record architecture decisions and known failure modes.
- [ ] Create a post-hackathon benchmark suite that cannot silently modify official metrics.

**Outcome:** A reproducible reference against which every later change is measured.

**Knowledge required:** Reproducible experiments require fixed code, data, configuration, model versions, and random seeds. A production enhancement that reduces search quality must be identified rather than hidden by unrelated changes.

**Alternatives:** A Git tag is simplest; an immutable release artifact is stronger.

**Completion gate:** A clean checkout reproduces final hackathon metrics and latency within documented tolerances.

## PH1 — Build a production Agent gateway

- [ ] Wrap the Agent contract in FastAPI endpoints.
- [ ] Add request/response models and error schemas.
- [ ] Add `/health`, `/ready`, and model-warmup behavior.
- [ ] Add configuration through environment variables.
- [ ] Add Docker packaging and a locked dependency file.
- [ ] Add CI for tests, linting, type checking, and a smoke evaluation.
- [ ] Add basic rate limiting, request IDs, and structured logging.

**Outcome:** Demonstrate the full development-to-launch lifecycle through a runnable backend service.

**Knowledge required:** FastAPI exposes typed HTTP endpoints; Docker packages runtime dependencies; readiness differs from liveness because a process may be alive before models and indexes are ready.

**Alternatives:** Flask is smaller, but FastAPI provides stronger schemas. A local Docker deployment is sufficient before adding a cloud target.

**Completion gate:** A container starts from one command, passes health checks, accepts concurrent sessions, and returns contract-valid responses.

## PH2 — Complete the LangGraph workflow migration

- [ ] Model session state with a typed graph-state schema.
- [ ] Convert deterministic pipeline functions into graph nodes.
- [ ] Add conditional edges for Buying, Browsing, Override, Boundary, overload cutoff, and fallback.
- [ ] Add checkpointing and replay.
- [ ] Compare graph and direct execution on identical fixtures.
- [ ] Document when the framework helps and when direct execution is preferable.

**Outcome:** Hands-on experience with a mainstream Agent framework while preserving the proven business logic.

**Knowledge required:** A state graph represents nodes as operations and edges as transitions. Framework adoption is valuable only when it improves visibility, checkpointing, branching, or maintenance.

**Alternatives:** If the hackathon adapter is already complete, promote and harden it. Evaluate another lightweight framework only for a documented comparison, not as a second production dependency.

**Completion gate:** Graph execution is behaviorally equivalent to the direct path, traceable, replayable, and covered by integration tests.

## PH3 — Formalize skill development and prompt operations

- [ ] Harden the typed skill registry with input/output schemas and capability metadata.
- [ ] Add skill versioning, timeouts, retries, permission metadata, and fallbacks.
- [ ] Add a local explanation or parsing model only where evaluation justifies it.
- [ ] Store prompts/context templates as versioned artifacts.
- [ ] Require structured outputs and validate them.
- [ ] Build prompt/context regression cases for overrides, missing facts, unsupported claims, and injection attempts.
- [ ] Record tokens, latency, model version, and template version in traces.

**Outcome:** Defensible hands-on evidence for skill development, prompt tuning, context engineering, and harness design.

**Knowledge required:** A skill is a bounded capability with a contract and operational policy. Prompt tuning is systematic versioned experimentation, not simply writing one prompt.

**Alternatives:** If a deterministic parser remains stronger, keep it and use prompt operations only for explanations or critic reasoning.

**Completion gate:** Every skill is independently testable, traceable, failure-isolated, and represented in the Agent capability registry.

## PH4 — Add a multi-agent constraint critic

- [ ] Define separate Planner and Critic responsibilities.
- [ ] Give the Critic read-only access to active constraints, catalog evidence, and proposed rankings.
- [ ] Require structured violation evidence rather than free-form opinions.
- [ ] Trigger the Critic only on low margin, route disagreement, or recent overrides.
- [ ] Allow bounded rerank or replan actions with loop limits.
- [ ] Evaluate quality, latency, and failure modes against the single-agent baseline.

**Outcome:** A purposeful multi-agent workflow in which independent verification improves recommendation reliability.

**Knowledge required:** Multi-agent systems justify their overhead when roles have different objectives, information access, or validation duties. Unbounded agent debate creates cost and nondeterminism without guaranteed quality.

**Alternatives:** A deterministic constraint verifier may remain the production default; the learned Critic can operate only on uncertain cases.

**Completion gate:** The Critic measurably improves constraint satisfaction or MRR on a held-out set without unacceptable latency and cannot loop indefinitely.

## PH5 — Build the Merchant Search Quality Analyst

- [ ] Define merchant questions and report consumers.
- [ ] Ingest anonymized session traces and retrieval diagnostics.
- [ ] Cluster failure modes by category, query, constraint, and retrieval stage.
- [ ] Identify missing or inconsistent catalog metadata.
- [ ] Quantify product discoverability and zero/overloaded-result causes.
- [ ] Generate evidence-linked operational recommendations.
- [ ] Create a reproducible sample merchant report and API endpoint.

**Outcome:** Extend the consumer shopping Agent into merchant product-operation assistance and business decision support.

**Knowledge required:** Operational analytics must connect recommendations to measurable evidence. The Analyst should distinguish catalog gaps, retrieval failures, ranking failures, and conversation-policy failures.

**Alternatives:** Begin with deterministic aggregation and templates; add an LLM summarizer only after the metrics are correct.

**Completion gate:** A sample report traces every recommendation back to aggregated session or catalog evidence and is useful for a concrete merchant decision.

## PH6 — Build the offline policy-learning lifecycle

- [ ] Define contextual-bandit state, action, and reward formally.
- [ ] Generate training episodes without leaking held-out evaluation labels.
- [ ] Train a baseline linear or tabular policy.
- [ ] Implement off-policy or simulator-based evaluation.
- [ ] Compare learned and heuristic policies on untouched sessions.
- [ ] Version policies and add safe fallback/rollback.
- [ ] Document overfitting, reward hacking, and distribution-shift risks.

**Outcome:** Genuine reinforcement-learning evidence for clarification and recommendation-depth optimization.

**Knowledge required:** The context describes the session, the action chooses a question/recommendation depth, and reward reflects conversion quality. A policy is useful only if evaluation separates training reward from unseen performance.

**Alternatives:** Use supervised imitation of the best heuristic before contextual bandits. Do not escalate to deep RL without evidence that simpler policies are insufficient.

**Completion gate:** A learned policy improves held-out TechnicalScore or another predeclared business metric and can be disabled instantly.

## PH7 — Add production evaluation, observability, and security

- [ ] Add OpenTelemetry-compatible traces and metric dashboards.
- [ ] Add latency, error, fallback, retrieval-drift, and policy-version metrics.
- [ ] Load-test concurrent isolated sessions.
- [ ] Test malformed input, prompt injection, data leakage, and unsupported product claims.
- [ ] Add dependency/model provenance and secret-scanning checks.
- [ ] Define service-level objectives and rollback procedures.
- [ ] Produce a failure-response runbook.

**Outcome:** Demonstrate reliable platform services rather than only a successful notebook or local demo.

**Knowledge required:** Observability combines logs, metrics, and traces. Security tests should reflect the actual Agent attack surface: untrusted text, tool inputs, catalog evidence, model outputs, and secrets.

**Alternatives:** Local dashboards and load tests are sufficient before deploying to paid cloud infrastructure.

**Completion gate:** The service meets documented latency/error objectives under load and security regression tests run in CI.

## PH8 — Produce portfolio and resume evidence

- [ ] Write a concise system-design document and architecture decision records.
- [ ] Publish a metric-backed before/after report.
- [ ] Record a short consumer flow and merchant-analysis demonstration.
- [ ] Document individual contribution, tradeoffs, failures, and lessons.
- [ ] Create accurate resume bullets with measured values.
- [ ] Add internship availability dates and education information separately.

**Outcome:** Translate the implementation into verifiable evidence for applications and interviews.

**Knowledge required:** Strong portfolio communication connects a business problem, architectural decision, implementation, measurement, limitation, and outcome. It never claims unimplemented capabilities.

**Alternatives:** A written case study can substitute for a polished demo UI; the backend and evidence are more important.

**Completion gate:** Every resume claim links to code, tests, a trace, a report, or a measured result.

---

## Post-hackathon experiment log

| Experiment | Baseline | Change | Quality result | Latency result | Decision |
|---|---|---|---|---|---|
| Not started | — | — | — | — | — |

## Post-hackathon decision log

| Date | Decision | Evidence | Revisit when |
|---|---|---|---|
| 2026-08-27 | Preserve the hackathon pipeline as the immutable baseline | Prevents portfolio additions from obscuring evaluated search quality | A later release has complete reproducibility and superior held-out results |
| 2026-08-27 | Add only purposeful multi-agent roles | Role separation must improve verification or merchant operations | A simpler deterministic component performs equally well |
| 2026-08-27 | Require evidence for RL and prompt-tuning claims | Prevents resume embellishment and reward overfitting | The corresponding evaluated lifecycle is implemented |
