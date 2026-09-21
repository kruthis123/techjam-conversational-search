# LC-03: What must be understood from a user message?

- Status: `Complete`
- Completion: User requested completion on 2026-09-11 after teach-back and tutor feedback.
- Prerequisites: LC-00, LC-01, LC-02
- Official requirement references: `docs/competition_specification.md`, `docs/agent_api_contract.json`, `docs/PROBLEM_MAP.md`

## Why this small problem matters

Understand what the customer requests without turning a preference, ambiguous phrase, or inferred need into an unsupported requirement.

## Questions to answer

1. What product and use case does the message describe?
2. Which statements express hard constraints, soft preferences, or acceptable alternatives?
3. What does a negation apply to?
4. Does new information add to or replace an earlier preference?
5. Which interpretations are explicit, inferred, ambiguous, or still unknown?
6. How could different interpretation methods be compared without choosing an architecture?

## Small experiment or exercise

Annotate a fictional shopping message with the exact phrases supporting product need, requirements, preferences, exclusions, alternatives, and unresolved ambiguity. Revise the interpretation after a follow-up correction.

## My teach-back answers

User's answers, recorded from the conversation:

1. "soft preference - Maybe blue color. Hard requirement - it must be blue"
2. "not belongs to the combination of words in this context and must be treated the same. Splitting the context and using the negation with individual requirements may lead to elimination of possible fits"
3. "leather is replaced with nylon, inside pocket in a new requirement added, must fit laptop remains"

Tutor feedback (not additional user-authored answers):

- The color example correctly contrasts a tentative preference with a hard requirement. "I'd prefer blue, but other colors are fine" expresses a clear soft preference with less uncertainty.
- Rejecting the red-and-canvas combination does not justify separately excluding every red product and every canvas product.
- The material changes from a soft leather preference to a hard nylon requirement because of "nylon only." The inside pocket is added and laptop fit remains required.

## My conclusion

The user's answers demonstrate preference strength, negation scope, and selective updates to meaning. The user requested completion; no architecture decision was made.

## Open questions

The carry-over from LC-02 was addressed through the soft-versus-hard example and tutor feedback on "nylon only." When ambiguity merits clarification and what evidence supports an inferred need remain topics for later learning. No interpretation method was selected.

## Evidence and sources

Ground contract facts in official repository documents. Label fictional examples and interpretation trade-offs as teaching examples, not official parser rules. Do not inspect application or evaluator source, private artifacts, or prior implementations.
