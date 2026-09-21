# LC-02: How does the simulated conversation evolve?

- Status: `Complete`
- Completion: User requested completion on 2026-09-11 after teach-back and tutor feedback.
- Prerequisites: LC-00, LC-01
- Official requirement references: `docs/competition_specification.md`, `docs/agent_api_contract.json`, `docs/evaluation_config.json`

## Why this small problem matters

Understand how an agent response affects the next simulated customer turn, how scenarios change the conversation, and when evaluation ends.

## Questions to answer

1. How do message, ask_attribute, and recommendations play different roles in a turn?
2. Who decides which information the simulated customer reveals?
3. How do Buying, Browsing, Intent Override, and Boundary differ?
4. When does a hit end a session, and what is special about Intent Override?
5. What does a reply expressing no preference establish?
6. Which simulator behavior is specified, and which details remain unknown?

## Small experiment or exercise

Write a short fictional exchange with a question, a structured ask_attribute, and a customer reply. Explain what the agent learns and whether another turn is permitted. Label illustrative dialogue separately from guaranteed simulator behavior.

## My teach-back answers

User's answers, recorded from the conversation:

1. "No, the evaluator terminates that session and scores it as soon as the target appears in the recommendations except for intent override where it waits until preference is overriden"
2. "I have no color preference increases the range of colors to recommend. Never discussing still does not give any information to take action upon colors"
3. "Message: Do you have a preferred material, ask_attribute: material, customer: yes leather. This new information can limit the search to leather materials confidently"

Tutor feedback (not additional user-authored answers):

- A terminating hit must be among the first 10 valid, unique catalog IDs. In Intent Override, an early appearance cannot convert; a qualifying hit must occur after the replacement intent arrives.
- No color preference establishes indifference. An unknown preference may already leave all colors available, so confirmed indifference need not increase the candidate range. Unknown preference permits recommendations without assuming a preferred color.
- The material question and ask_attribute agree, and the reply establishes a leather preference. Preferred does not necessarily mean required: excluding every other material assumes more than the reply establishes.

Optional follow-up: How would "I'd prefer leather, but nylon is fine" change a decision to exclude non-leather bags? The user requested completion and the next lesson rather than answering this follow-up. This distinction carries into LC-03; it is not recorded as independently verified.

## My conclusion

The user's answers address termination, preference information, and a structured material question. Tutor refinements clarify eligible hits, indifference versus uncertainty, and preference versus requirement. The user requested completion; no architecture decision was made.

## Open questions

Exact handling of repeated questions, null, other, and prose/ask_attribute mismatches remains unspecified in the inspected documents. Preferred versus required needs further practice in LC-03. Do not infer exact simulator reply rules from hypothetical examples.

## Evidence and sources

Use only official repository documentation and minimal permitted samples if required. Do not inspect evaluator or application source, prior implementations, or private artifacts.
