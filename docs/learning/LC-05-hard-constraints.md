# LC-05: How can hard constraints be applied safely?

- Status: `Complete`
- Completion: User requested completion on 2026-09-13 after teach-back and tutor feedback.
- Prerequisites: LC-00 through LC-04
- Official requirement references: `docs/competition_specification.md`, `docs/agent_api_contract.json`, `docs/PROBLEM_MAP.md`

## Why this small problem matters

A true hard constraint should prevent unsuitable recommendations, but an interpretation or metadata error can wrongly remove the hidden target.

## Questions to answer

1. What evidence makes a customer condition a hard constraint?
2. How can customer wording and catalog values be normalized without changing meaning?
3. How should missing or ambiguous catalog metadata differ from a known mismatch?
4. How do contradictory constraints arise and what can be concluded from them?
5. When would relaxing a constraint violate the customer's request?
6. How can false exclusions be detected and compared without selecting an architecture?

## Small experiment or exercise

Given a fictional request and small product table, classify products as confirmed match, confirmed mismatch, or unknown for each hard constraint. Explain which exclusions are justified and which would be false exclusions.

## My teach-back answers

User's answers, recorded from the conversation:

1. "It is not a contradicting claim but a truly unknown attribute so must not be considered as a mismatch"
2. "B can be excluded because its material is polyester while nylon is a hard user requirement"
3. "Flase exclusion removes the product from the candidate list and ranking runs only over the candidate list"

Tutor feedback (not additional user-authored answers):

- Missing metadata supplies evidence of neither satisfaction nor violation, so laptop fit remains unknown.
- B is a confirmed mismatch because polyester contradicts "nylon only"; its blue color cannot compensate for the hard-constraint violation.
- Ranking only orders retained candidates. A falsely excluded target requires another retrieval or verification step before ranking can recover it.

## My conclusion

The user understands unknown versus mismatch, evidence-backed exclusion, and how false exclusion prevents downstream ranking from recovering a target. The user requested completion; no constraint-handling architecture was selected.

## Open questions

Safe normalization boundaries, contradiction handling, and any constraint-relaxation policy remain unresolved. No policy was selected.

## Evidence and sources

Ground competition facts in official repository documentation. Label conceptual policies and fictional examples as teaching material rather than contract requirements. Do not inspect application or evaluator source, private artifacts, prior implementations, or previous results.
