# LC-11: How can strategy change at runtime?

- Status: `Complete`
- Completion: User requested completion on 2026-09-15 after teach-back and tutor feedback.
- Prerequisites: LC-00 through LC-10
- Official requirement references: `docs/competition_specification.md`, `docs/agent_api_contract.json`, `docs/evaluation_config.json`, `docs/PROBLEM_MAP.md`

## Why this small problem matters

Different conversation conditions may make different behaviors useful. Switching without reliable evidence can create instability, while never adapting can repeat a failing behavior.

## Questions to answer

1. Which observable signals could justify choosing or switching behavior?
2. How can failure be detected without access to the hidden target?
3. What is the difference between a fallback and an unprincipled strategy change?
4. How can repeated questions, unchanged candidates, low evidence, and time remaining affect a decision?
5. Why do deterministic controls, bounded retries, and traceable reasons matter?
6. How can adaptive behavior be compared without choosing an architecture?

## Small experiment or exercise

Given a fictional multi-turn session, identify observable signals at each turn, select among several conceptual actions, and explain whether a switch is justified. Record a fallback condition and a stopping condition without assuming access to the hidden target.

## My teach-back answers

User's answers, recorded from the conversation:

1. "Because they keep recommending same list of products which clearly do not have the target as the evaluator is not ending the session"
2. "empty candidate set, no change in candidate rankings, conflicting constraints etc"
3. "Colldown waits for a while before a second switch can happen so that the recommended candidates can stabilize without hastily switching strategy"

Tutor feedback (not additional user-authored answers):

- Session continuation establishes that no eligible conversion occurred. In ordinary sessions, repeating the same valid list is strong evidence that continuing unchanged is unproductive; unchanged internal rankings alone are only a proxy, and Intent Override has a pre-override exception.
- Empty candidates, unchanged rankings, and conflicts are fallback triggers. A principled fallback also defines its permitted action, preserved hard requirements, retry bound, and stopping condition.
- Cooldown gives a changed strategy time to produce evidence before another switch and reduces rapid oscillation; stabilization should be judged through meaningful result changes rather than elapsed time alone.

## My conclusion

The user understands runtime failure signals and cooldown behavior. Tutor feedback distinguishes triggers from fully specified bounded fallbacks and direct session evidence from internal proxies. The user requested completion; no routing, switching, fallback, or control architecture was selected.

## Open questions

Sufficient stagnation evidence, permitted relaxation, retry bounds, stopping behavior, and cooldown strength remain unresolved. No runtime-control policy was selected.

## Evidence and sources

Ground competition facts in official repository documentation. Label strategy signals, policies, and fictional examples as teaching material rather than official behavior. Do not inspect application or evaluator source, private artifacts, prior implementations, or previous results.
