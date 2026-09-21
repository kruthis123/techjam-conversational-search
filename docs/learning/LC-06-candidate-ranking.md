# LC-06: How can candidates be ordered?

- Status: `Complete`
- Completion: User requested completion on 2026-09-14 after teach-back and tutor feedback.
- Prerequisites: LC-00 through LC-05
- Official requirement references: `docs/competition_specification.md`, `docs/evaluation_config.json`, `docs/agent_api_contract.json`, `docs/PROBLEM_MAP.md`

## Why this small problem matters

Once the target is present among candidates, its final position determines whether it enters the scored top ten and how much reciprocal-rank credit it receives.

## Questions to answer

1. Which evidence can contribute to a candidate's ranking score?
2. How should hard-constraint evidence differ from soft-preference evidence?
3. How can scores from different retrieval signals be combined fairly?
4. How do rule-based, learned, and reranking methods differ?
5. What does score calibration mean, and why can raw scores be incomparable?
6. How can ranking quality be tested separately from candidate retrieval coverage?

## Small experiment or exercise

Given a fixed fictional candidate set, order products using stated evidence and explain each pairwise decision. Then identify how a misleading signal could push the target outside the scored top ten.

## My teach-back answers

User's answers, recorded from the conversation:

1. "The scores were produced on different scales and lack relativity leading to higher magnitude scores getting preferences even though they lie towards the lower side in their range"
2. "If the candidates were mixed up between tests then one combination may have favoured a particular reranking strategy but that does not work well in general. Therefore the candidate sets must be fixed"
3. "User had a hard constraint on the material being nylon. B's material directly contradicts this claim and must be disregarded"

Tutor feedback (not additional user-authored answers):

- Raw score magnitudes are not directly meaningful across systems with different units, ranges, and distributions.
- Fixed candidate sets isolate ranking effects from retrieval effects. Generalization should then be tested across multiple fixed sets from unseen cases.
- B is a confirmed hard-constraint violation; rating and lexical relevance do not establish suitability for the request.

## My conclusion

The user understands score incomparability, controlled ranking comparisons, and the priority of confirmed hard constraints over unrelated positive signals. The user requested completion; no ranking method or scoring formula was selected.

## Open questions

Signal choice, fusion, calibration, tie-breaking, and reranking behavior remain unresolved. No ranking method was selected.

## Evidence and sources

Ground competition facts in official repository documentation. Label conceptual scoring examples and method comparisons as teaching material rather than official requirements. Use a fixed candidate set so retrieval and ranking effects remain distinguishable. Do not inspect application or evaluator source, private artifacts, prior implementations, or previous results.
