# LC-08: When is a clarification worth a turn?

- Status: `Complete`
- Completion: User requested completion on 2026-09-14 after teach-back and tutor feedback.
- Prerequisites: LC-00 through LC-07
- Official requirement references: `docs/competition_specification.md`, `docs/agent_api_contract.json`, `docs/evaluation_config.json`, `docs/PROBLEM_MAP.md`

## Why this small problem matters

A question can reduce uncertainty and improve later recommendations, but an unhelpful question consumes a limited turn and delays a possible hit.

## Questions to answer

1. What uncertainty would a proposed question resolve?
2. Could the simulator provide useful information for the chosen ask_attribute?
3. How much would each plausible answer change the candidate set or ordering?
4. What is the opportunity cost of asking rather than relying on current evidence?
5. When can recommendations and a clarification be returned together?
6. How can clarification policies be compared without choosing an architecture?

## Small experiment or exercise

Given a fictional request, candidate set, and two possible questions, predict the plausible replies and how each would change the candidates or ranking. Decide whether to ask, recommend, or do both, and state the uncertainty behind the decision.

## My teach-back answers

User's answers, recorded from the conversation:

1. "If the answer received does not help to eliminate candidates or reorder ranking then the new information rendered the turn useless"
2. "The attribute must be specified among candidates to filter out and it should be useful attribute that can remove uncertainty"
3. "Do both. laptop size and colour are attributes that are present in all catalog items and we do not have confirmed user requirements in these domains yet"

Tutor feedback (not additional user-authored answers):

- An unchanged action identifies a low-value question. Even an informative answer can hurt if asking delays a target that could already have been recommended successfully.
- An answer is actionable when it resolves decision-relevant uncertainty and candidate metadata contains enough evidence to apply it; the simulator must also be able to reveal the information.
- Asking and recommending together is defensible in the fictional example. Laptop-size evidence was missing for one candidate, and black was already an explicit soft preference, so laptop size had greater likely action impact than color.

## My conclusion

The user understands that clarification value depends on reducing actionable uncertainty and chose to ask while recommending in the fictional example. The user requested completion; no universal clarification policy or architecture was selected.

## Open questions

Exact answerability by attribute, expressions of no preference, useful-question frequency, and a decision threshold for spending a turn remain unresolved. No clarification policy was selected.

## Evidence and sources

Ground competition facts in official repository documentation. Label question-value concepts, hypothetical replies, and policy comparisons as teaching material rather than guaranteed simulator behavior. Do not inspect application or evaluator source, private artifacts, prior implementations, or previous results.
