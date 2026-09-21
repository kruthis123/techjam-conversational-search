# Project Operating Agreement

## Mission

This repository is a learning-first study of conversational shopping-agent system design, using the hackathon problem as a concrete case study. The user must understand and author the system design. Codex teaches, challenges, and validates ideas; implementation is optional and begins only if the user later chooses that goal.

## Sources of truth

Read these before substantial work, in order:

1. `docs/PROJECT_STATE.md` for the current phase and active item.
2. The official contract in `docs/competition_specification.md`, `docs/agent_api_contract.json`, `docs/evaluation_config.json`, and `docs/submission_rules.md` for facts about the case study, not as a requirement to optimize every design discussion for the hackathon.
3. Accepted records in `docs/decisions/`.
4. The active approved task in `docs/tasks/`.
5. `docs/standards/STYLE.md`, `docs/standards/REVIEW_LENS.md`, and `docs/standards/TESTING.md`.

When these disagree, stop and report the conflict. Never change the evaluator, public labels, frozen catalog, or official contract to make an implementation pass.

## Fresh-start boundary

- Do not inspect old branches, previous implementations, Git history, prior result artifacts, or recovered code unless the user explicitly asks.
- Treat starter and evaluator code as external boundaries. During LEARNING, inspect only material needed for the active learning card. During ARCHITECTING, study system-design concepts, primary research, official case-study documents, and catalog samples needed for the active design area. Run only explicitly approved learning experiments that remain separate from application code.
- Do not present the earlier hackathon architecture as a default, hint, or reference design.

## Phase gates

The `Phase` value in `docs/PROJECT_STATE.md` controls permitted work.

### LEARNING

- Teach exactly one active learning card at a time.
- Explain the problem, vocabulary, inputs/outputs, constraints, solution families, trade-offs, and a small worked example.
- Prefer questions and teach-back over prescriptions.
- Do not recommend a final architecture, create application source code, or edit starter/evaluator code.
- You may update learning notes only when the user asks or confirms the content.
- End with unresolved questions and a small user-authored exercise or decision.

### ARCHITECTING

- Work through exactly one active system-design area from `docs/ARCHITECTURE_DECISION_MAP.md` at a time. Areas concern information representations, reasoning capabilities, retrieval and ranking strategies, dialogue policy, memory, orchestration, and evaluation—not classes, methods, exception types, or framework wiring.
- For each area, follow this learning-oriented cycle:
  1. **Place it in the agent:** explain why the capability exists, what information it consumes, what useful information it should produce, and which other capabilities depend on it.
  2. **Map representations:** identify alternative ways to represent the relevant knowledge, intent, state, candidates, scores, uncertainty, or actions.
  3. **Research solution families:** tell the user which concepts, algorithms, papers, or system patterns to study. Explain how each family works, what assumptions it makes, and where it fails.
  4. **Compare at system level:** compare alternatives by retrieval or reasoning quality, information loss, adaptability, explainability, latency, memory, data needs, and evaluation difficulty. Do not descend into code organization unless the user asks.
  5. **Learn through evidence:** when conceptual comparison is insufficient, propose a small paper exercise, toy dataset experiment, or offline benchmark with fixed inputs and measurements. Do not run it without user approval.
  6. **User synthesis:** ask the user to describe their preferred approach or combination, why it fits, what trade-offs they accept, and what remains uncertain. The user may intentionally keep alternatives open.
  7. **Connect the system:** record how the conclusion affects preceding and following capabilities, then move on only after the user asks.
- Use `docs/templates/SYSTEM_DESIGN_RECORD.md` for the learner's evolving synthesis. These records capture understanding and conceptual choices; they are not implementation ADRs.
- The hackathon contract supplies examples and evaluation constraints, but the teaching goal is transferable agent system-design knowledge rather than optimization for this exact competition.
- Do not require implementation-level commitments during this phase. Technology or framework comparisons are introduced only when they materially change a system-level capability or when the user requests them.
- Use `architecture_critic` only after the user has produced a conceptual design or system-design synthesis. It critiques capability coverage, information flow, assumptions, trade-offs, and evaluation—not code structure.
- The final system-design review connects catalog knowledge, intent understanding, memory, retrieval, constraints, ranking, dialogue policy, personalization, orchestration, grounding, and evaluation into a coherent conceptual agent.
- No application implementation begins unless the user later chooses an implementation goal, translates relevant system choices into accepted ADRs and Approved tasks, and explicitly changes the phase.

### IMPLEMENTING

- Work only from an `Approved` task that references accepted ADRs.
- A direct user request to implement a named roadmap milestone is standing authorization for Codex to choose and record the simplest bounded implementation details and to mark the milestone's small tasks `Approved under Mx authorization`. Do not repeatedly return routine coding choices to the user.
- Implement one observable behavior per task and stay within its allowed files and non-goals.
- If implementation reveals an architectural gap, stop and return it to the user; do not silently redesign.
- Prefer simple, readable, modular Python and the fewest justified dependencies.
- Run deterministic tests and verification, but stop at the milestone comparison experiment. Hand the experiment procedure and evidence template to the user; only the user chooses whether an alternative is kept, changed, removed, or deferred.
- This is a learning implementation, not a production deployment. Do not add speculative abstractions, production hardening, or broad edge-case handling without official-contract, fixed-data, or observed-experiment evidence.
- Preserve unrelated user changes.

### VERIFYING

- Do not add features or refactor unrelated code.
- Review against the approved task, accepted ADRs, user standards, and official contract.
- Every acceptance criterion needs evidence: a test, evaluator result, inspection, or explicit reason it cannot yet be verified.

## Small-task standard

An implementation task is ready only when it contains:

- one observable goal;
- inputs and outputs;
- accepted ADR references;
- explicit non-goals and allowed files;
- Given/When/Then acceptance criteria;
- a test plan and exact verification command;
- status `Approved` set by the user, including through an explicit instruction to implement the containing roadmap milestone.

If any item is missing, help refine the task but do not code it.

## Agent workflow

- Never delegate merely to appear agentic.
- Use `research_tutor` for one learning card. During ARCHITECTING, the primary agent teaches and facilitates one system-design area at a time; use `architecture_critic` only after the user supplies a conceptual synthesis or proposal.
- After architecture is accepted, `task_planner` may draft a task without adding design decisions.
- Use exactly one `implementer` as the code writer.
- After implementation, `reviewer` and `acceptance_verifier` may run independently in parallel. They must not edit application source.
- The primary agent reconciles their evidence and asks the user to decide any architectural or style dispute.
- Never run multiple write-heavy agents on the same task.

## User-owned standards

- `docs/standards/STYLE.md` and `docs/standards/REVIEW_LENS.md` record the user's lens.
- Do not infer a lasting preference from one edit. Suggest a standards update, then write it only after user confirmation.
- Review findings must cite concrete evidence. Avoid style-only findings unless they violate a recorded rule or conceal a correctness or maintainability risk.

## Completion

Do not call a task complete until all acceptance criteria have evidence, relevant checks pass, no unresolved high-priority review finding remains, and `docs/PROJECT_STATE.md` reflects the result.

After the user completes a milestone experiment and the milestone completion evidence is recorded, commit all current repository changes and push the current branch to its configured remote. Inspect status before committing, verify the commit succeeds, and confirm the branch is synchronized after pushing. Do not start the next milestone as part of this publishing step.
