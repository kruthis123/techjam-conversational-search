# LC-00: What exactly is evaluated?

- Status: `Complete`
- Completion: User requested completion on 2026-09-11; numerical exercise intentionally skipped, not verified.
- Prerequisites: None
- Official requirement references: `README.md`, `docs/competition_specification.md`, `docs/agent_api_contract.json`, `docs/evaluation_config.json`

## Why this small problem matters

Before designing behavior, I need to know what the environment sends, what my agent may return, when a session ends, and how every outcome changes the score.

## Questions to answer

1. What calls occur from session reset through termination?
2. Which response fields affect scoring, simulation, or feasibility reporting?
3. What exactly counts as a hit, miss, rank, and first-hit turn?
4. How do Hit Rate@10, MRR, MTTC, Efficiency, and TechnicalScore react to the same example session?
5. What is special about an Intent Override session before the override arrives?
6. Which metrics are global, and which are sliced by scenario?
7. What invalid outputs are filtered and what failures may become misses?

## Exercise

Create three imaginary sessions—an early rank-1 hit, a later rank-5 hit, and a miss—and calculate every metric contribution by hand. Then explain which design behavior each metric rewards.

## My teach-back answers

User's answers, recorded from the conversation:

1. "reset received unique session id and a user profile containing user preferences from past purchases. The agent receives a user message explaining what they want to shop. The agent can reply with recommendations, question and ask_attribute which is used by simulator to form response. ask_attribute is the output field that tells the simulator what attribute was asked about"
2. "duplicates are reduced to 1, invalids ids are eliminated before ranking. Intent override consists of a change in preference on 3rd/4th turn so the evaluator is designed to wait until then before judging"
3. "I have theoritically understood the metrics and don't want to get into the math for this session"

Tutor feedback (not additional user-authored answers):

- The profile contains safe aggregate summaries and preference tags, not raw purchase history. Each respond call also supplies session_id, turn, and top_k.
- Invalid and duplicate IDs are removed before scored ranks are assigned. The precise Intent Override rule blocks successful conversion before the replacement intent arrives, rather than postponing all evaluation.
- HitRate measures success, MRR rewards higher placement, and MTTC/Efficiency reward earlier success. TechnicalScore combines these outcomes. Numerical calculation was not assessed.

## My conclusion

The user reports conceptual understanding of the metrics and requested that LC-00 be marked complete before starting LC-01. No architecture decision was made.

## Open questions

The numerical exercise remains unpractised by user choice. Exact runtime limits, detailed simulator reply rules, and whether particular failures lose a turn or a session remain unspecified in the inspected contract documents.

## Evidence and sources

Use only the official repository documents listed above for this card.
