# LC-14: How will your decisions become a coherent system?

- Status: `Complete`
- Completion date: `2026-09-15`
- Prerequisites: LC-00 through LC-13
- Official requirement references: `docs/competition_specification.md`, `docs/agent_api_contract.json`, `docs/evaluation_config.json`, `docs/submission_rules.md`, `docs/PROBLEM_MAP.md`

## Why this small problem matters

The learned capabilities must eventually fit together so that inputs, state, evidence, candidates, questions, recommendations, failures, and measurements have clear ownership and consistent interfaces.

## Questions to answer

1. What capability boundaries are needed, and what responsibility belongs at each boundary?
2. What information flows from reset and a turn request to the final response?
3. Who owns session state, constraint status, candidates, ranking evidence, and fallback decisions?
4. What interface assumptions could make independently reasonable capabilities disagree?
5. Where can failures occur, and what valid behavior should follow each failure?
6. Which observations and test seams would make every important decision inspectable?

## Small experiment or exercise

Draft a capability map for one fictional turn using boxes and arrows or a numbered flow. For every boundary, state its input, output, owner, failure behavior, and one observable test. Mark unresolved design choices instead of silently deciding them.

## My teach-back answers

1. "During message understanding, if not preferred is interpretted as preferred then user intent is corrupted"
2. "An attribute specified as a requirement should be maintained throughout until the list of recommendations sent where the recommended list must meet the requirement"
3. "Failure in receiving the target in the top k could be because of reranking when the target is present in candidates but lost after ranking"

## Tutor feedback

- The negation example correctly identifies a boundary where meaning can be corrupted.
- A hard requirement must remain an invariant across the turn. If no candidate satisfies it, the system needs an explicit question, explanation, or defined fallback rather than silently relaxing it.
- A target present before ranking but absent from the top `k` identifies a ranking-stage failure. Candidate membership before ranking, ranking contributions, and final position provide evidence for diagnosing it.

## My conclusion

Meaning, constraint strength, and diagnostic evidence must survive capability boundaries end to end. Local correctness is insufficient when a later boundary corrupts user intent or removes a viable target. No architecture has yet been proposed or accepted.

## Open questions

- Where will canonical constraint state live, and who may change or relax it?
- How will candidate, exclusion, ranking, and fallback evidence cross boundaries?
- Who owns final response validation and end-to-end contract behavior?
- Which failure paths and test seams will the user's architecture define?

## Evidence and sources

Ground competition facts in official repository documentation. Label capability examples, interface alternatives, and fictional flows as teaching material rather than a recommended architecture. Do not inspect application or evaluator source, private artifacts, prior implementations, or previous results.
