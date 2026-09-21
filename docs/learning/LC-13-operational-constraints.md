# LC-13: What operational constraints matter?

- Status: `Complete`
- Completion: User requested completion on 2026-09-15 after teach-back and tutor feedback.
- Prerequisites: LC-00 through LC-12
- Official requirement references: `docs/competition_specification.md`, `docs/agent_api_contract.json`, `docs/evaluation_config.json`, `docs/submission_rules.md`, `docs/PROBLEM_MAP.md`

## Why this small problem matters

A method that produces good recommendations during development may still fail official evaluation if it times out, requires unavailable network access, cannot be reproduced, consumes excessive resources, or emits invalid usage information.

## Questions to answer

1. Which runtime limits and environment assumptions are specified, and which remain unknown?
2. How do latency, memory, dependency size, network access, and model cost affect feasibility?
3. What must usage reporting contain, and when is it optional?
4. What makes behavior deterministic or reproducible enough to diagnose and compare?
5. What should an offline or degraded-mode fallback preserve?
6. How can operational choices be compared without selecting an architecture?

## Small experiment or exercise

Given several fictional agent variants, identify which could fail under offline, timeout, dependency, or reproducibility constraints. State what evidence would be needed before choosing among them.

## My teach-back answers

User's answers, recorded from the conversation:

1. "timeouts are considerd as a miss"
2. "can be omitted when not using llm. Must contains token usage info"
3. "CPU, memory, timeout"

Tutor feedback (not additional user-authored answers):

- Latency matters because excessive latency can cause a timeout that may count as a miss, and it also affects practical feasibility.
- Usage may be omitted when no model is used. If returned, it contains nonnegative integer prompt_tokens and completion_tokens.
- CPU, memory, and timeout limits are essential but incomplete comparison evidence. Network availability, cold start and per-turn latency, peak memory and package size, clean installation, offline behavior, failure containment, scenario quality, cost, and repeat-run variability are also needed.

## My conclusion

The user understands timeout risk and usage reporting, and identified major unspecified resource limits. Tutor feedback supplied the remaining operational evidence needed for comparison. The user requested completion; no operational architecture, dependency policy, model choice, or fallback was selected.

## Open questions

Exact CPU, memory, storage, timeout, Python, and network limits; packaged-index rules; clean-environment behavior; and acceptable operational thresholds remain unresolved. No operational approach was selected.

## Evidence and sources

Ground competition facts in official repository documentation. Label operational budgets, failure examples, and comparison policies as teaching material rather than organizer guarantees. Do not inspect application or evaluator source, private artifacts, prior implementations, or previous results.
