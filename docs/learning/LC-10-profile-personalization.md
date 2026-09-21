# LC-10: How can the aggregate user profile help safely?

- Status: `Complete`
- Completion: User requested completion on 2026-09-14 after teach-back and tutor feedback.
- Prerequisites: LC-00 through LC-09
- Official requirement references: `docs/competition_specification.md`, `docs/agent_api_contract.json`, `docs/evaluation_config.json`, `docs/PROBLEM_MAP.md`

## Why this small problem matters

The aggregate profile may help when the current request is vague, but historical tendencies are weaker evidence than the customer's present statements and can cause over-personalization.

## Questions to answer

1. What profile fields are available, and what does each establish or leave unknown?
2. Why is a profile preference a prior rather than a current requirement?
3. How should current explicit evidence affect a conflicting profile tendency?
4. When can profile evidence help with a cold or vague request?
5. What failures indicate over-personalization or unsupported assumptions?
6. How can profile use be compared without choosing an architecture?

## Small experiment or exercise

Given a fictional aggregate profile and three current requests, identify where the profile may break a tie, where it should be ignored, and where it could cause an unsupported exclusion. Explain the evidence priority in each case.

## My teach-back answers

User's answers, recorded from the conversation:

1. "A user may be shopping for a different occasion or for someone else"
2. "When the evidence is about the same product and there is high ambiguity"
3. "The user always purchases casual jewellery but now wants to purchase grand jewellery for a function. Eliminating grand jewellery will eliminate the target"

Tutor feedback (not additional user-authored answers):

- Historical behavior may describe another occasion, recipient, or earlier preference, so it cannot establish present intent.
- Profile evidence may break a tie when it is relevant to the current product category or decision, candidates satisfy current evidence similarly, and no current statement conflicts with it. Ambiguity alone is insufficient if the profile is unrelated.
- Excluding grand jewellery based on casual-jewellery history would override the explicit present purpose and could remove the target.

## My conclusion

The user understands profile information as a historical prior, the need for relevance when tie-breaking, and the risk of over-personalization overriding current intent. The user requested completion; no personalization policy or architecture was selected.

## Open questions

Profile-value semantics, conflict thresholds, cold-start behavior, and appropriate influence strength remain unresolved. No personalization policy was selected.

## Evidence and sources

Ground competition facts in official repository documentation. Label profile-use examples and policy comparisons as teaching material rather than official behavior. Do not inspect application or evaluator source, private artifacts, prior implementations, or previous results.
