# LC-09: How should replaced or absent preferences behave?

- Status: `Complete`
- Completion: User requested completion on 2026-09-14 after teach-back and tutor feedback.
- Prerequisites: LC-00 through LC-08
- Official requirement references: `docs/competition_specification.md`, `docs/agent_api_contract.json`, `docs/evaluation_config.json`, `docs/PROBLEM_MAP.md`

## Why this small problem matters

The agent must stop applying a superseded preference after an intent override and must distinguish an explicit absence of preference from missing information.

## Questions to answer

1. What evidence indicates replacement rather than addition?
2. Which earlier facts are superseded, and which unrelated facts remain active?
3. How does an explicit no-preference reply differ from unknown or conflicting information?
4. What stale-state failures can affect retrieval and ranking after an override?
5. What recovery is possible when replacement or absence is ambiguous?
6. How can override and boundary handling be compared without choosing an architecture?

## Small experiment or exercise

Track a fictional request through an explicit material replacement and a no-color-preference reply. After each message, identify active, superseded, unknown, and indifferent attributes, then explain which prior filters or ranking signals must stop applying.

## My teach-back answers

User's answers, recorded from the conversation:

1. "There was no change made to budget requirement so the initial requirement holds and must hold all the way"
2. "If colour was never discussed then there is uncertainty because the user might have some colour preference which is yet to be discovered. When no colour preference is established then we can be certain about the colour claim and recommend all available colours"
3. "cached candidates, cached search queries, historical summaries"

Tutor feedback (not additional user-authored answers):

- The budget remains active because the material correction does not affect it; it remains until changed later or the session resets.
- Undiscussed color is unknown, while no color preference establishes indifference. Any color may be considered with respect to color, while all other active requirements still apply.
- Stale leather influence can persist in cached candidates, rewritten queries, summaries, active filters, ranking boosts, and penalties.

## My conclusion

The user understands selective invalidation, preserving unrelated requirements, indifference versus unknown, and hidden stale-state effects. The user requested completion; no override-detection, invalidation, or recovery architecture was selected.

## Open questions

Implicit replacement evidence, unresolved conflicts, exact no-preference wording, and acceptable recovery cost remain unresolved. No approach was selected.

## Evidence and sources

Ground competition facts in official repository documentation. Label detection and recovery concepts and fictional dialogue as teaching material rather than guaranteed simulator behavior. Do not inspect application or evaluator source, private artifacts, prior implementations, or previous results.
