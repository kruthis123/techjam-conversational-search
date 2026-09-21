# Learning-to-Implementation Workflow

## Why this harness is staged

The main Codex task holds your requirements and decisions. Specialized agents keep research, code logs, review, and test output out of that central context. Only one agent writes code, which keeps ownership and diffs clear.

## 1. Learn one small problem

Copy `docs/templates/LEARNING_CARD.md` into `docs/learning/LC-XX-short-name.md`, then use:

```text
We are in LEARNING. Use the research_tutor agent for LC-XX only. Teach me the problem and solution families, but do not recommend an architecture or edit source code. End with three teach-back questions.
```

Answer the teach-back yourself. Ask Codex to record only the conclusions you confirm.

## 2. Learn agent system design one capability at a time

After the learning cards are complete, enter ARCHITECTING only with explicit approval. Use `docs/ARCHITECTURE_DECISION_MAP.md` as a study map and work on one system-design area at a time. The hackathon is the running example, but the goal is transferable understanding of agent systems.

Start an area with:

```text
We are in ARCHITECTING. Work on SD-XX only. Teach me where this capability fits, useful information representations, solution families, system-level trade-offs, and failure modes. Tell me what to research and propose a small learning experiment only if comparison needs evidence. Ask me to synthesize my approach, but do not choose it for me or descend into code-level design.
```

For each active area:

1. **Place it in the agent:** Understand the capability's purpose and its relationships to the rest of the system.
2. **Explore representations:** Compare ways to represent the information it consumes and produces.
3. **Study solution families:** Learn relevant algorithms and agent patterns, including their assumptions and failure modes.
4. **Compare system trade-offs:** Consider quality, information loss, adaptability, explainability, latency, memory, data requirements, and evaluation difficulty.
5. **Use a learning experiment when needed:** Approve a paper exercise, toy dataset comparison, or offline benchmark only when evidence would distinguish alternatives.
6. **Write your synthesis:** Use `docs/templates/SYSTEM_DESIGN_RECORD.md` to explain your preferred approach or combination, reasoning, trade-offs, and open questions. You may keep a choice unresolved when evidence is insufficient.
7. **Connect it:** Explain what the synthesis requires from upstream capabilities and provides to downstream capabilities.

After your synthesis, you may ask for a system-design critique:

```text
Use the architecture_critic agent to challenge SDR-XXX at the system-design level. Do not replace my design or discuss code structure. Return missing capabilities, information-flow gaps, unresolved trade-offs, and useful learning experiments.
```

After all areas, draw an end-to-end conceptual agent showing how catalog representations, intent, memory, retrieval, constraints, ranking, dialogue policy, personalization, orchestration, grounding, and evaluation interact. Implementation remains optional.

## 3. Prepare one roadmap milestone

After the milestone roadmap is approved, invoke the reusable planning skill:

```text
Use $milestone-adr-task-planner to prepare the next roadmap milestone, draft its necessary ADRs, and produce one implementation task for my approval.
```

The skill will inspect the milestone and inherited decisions, separate implementation decisions from experimental parameters and local task details, and ask only the clarifications that materially affect the documents. It drafts focused ADRs first. After you explicitly accept the required ADRs, it drafts one small task without adding new architecture decisions.

Approve in this order: milestone scope, required ADRs, one task, then the phase transition. A task remains `Draft` until you explicitly approve it; implementation must not begin merely because the task document exists.

## 4. Implement, review, and verify

```text
Implement the active Approved task with one implementer agent. After it finishes, run reviewer and acceptance_verifier independently in parallel. Reconcile their evidence, but do not fix or waive anything until I review it.
```

The normal loop is:

```text
one implementer -> reviewer + acceptance_verifier -> your decision -> focused correction -> final verification
```

Review and verification agents never edit application source. Architectural gaps return to ARCHITECTING rather than being patched around.

At a milestone experiment checkpoint, Codex hands the comparison to the user. After the user records the keep/change/defer decision and the milestone evidence is complete, Codex commits all current repository changes and pushes the current branch. The next milestone still requires a separate user request.

## 5. Teach the harness your lens

When you repeatedly correct naming, structure, error handling, testing, or review priorities, decide whether it is a durable rule. If yes, explicitly ask Codex to add it to `STYLE.md` or `REVIEW_LENS.md`, including one accepted example. Agents may suggest a rule but cannot silently create one.

## Start now

Check `docs/PROJECT_STATE.md`. If learning is incomplete, continue its active card. In ARCHITECTING, mark exactly one system-design area active and use the system-design prompt above. New Codex tasks should be started or restarted after harness configuration changes so project instructions and custom agents are reloaded.
