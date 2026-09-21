# LC-07: What state must survive across turns?

- Status: `Complete`
- Completion: User requested completion on 2026-09-14 after teach-back and tutor feedback.
- Prerequisites: LC-00 through LC-06
- Official requirement references: `docs/competition_specification.md`, `docs/agent_api_contract.json`, `docs/PROBLEM_MAP.md`

## Why this small problem matters

Each turn request contains the current message rather than a complete history field. The agent must understand which earlier facts remain active, which are uncertain, and which have been replaced, while keeping sessions isolated.

## Questions to answer

1. What is the difference between an observation, an inferred belief, and an active preference?
2. Why do provenance and confidence matter when later messages revise earlier information?
3. Which facts should remain active, be superseded, or become unresolved across turns?
4. What does reset mean for session isolation and stale state?
5. What information can be compressed without changing the customer's meaning?
6. How can state handling be compared without choosing an architecture?

## Small experiment or exercise

Track a fictional request across several turns. After each message, list active requirements, soft preferences, unknowns, superseded information, provenance, and confidence. Explain what reset must remove before a new session.

## My teach-back answers

User's answers, recorded from the conversation:

1. "Explicit observation indicates higher confidence in enforcing the constraint as it relies on exact keywords mentioned. Inferred belief is relatively lesser confidence as it is based on assumptions and not explicit claims made"
2. "Turn 3 cancels overrides the material requirement with nylon especially with the \"no\" phrase so it must be superseded and nylon must be enforced instead"
3. "All stored information must be reset as the new session belongs to a new user requesting a new product"

Tutor feedback (not additional user-authored answers):

- Explicit evidence usually supports higher confidence than inference, but explicit does not automatically mean hard; wording can be explicit without using exact keywords.
- Turn 3 explicitly rejects the earlier soft leather preference and establishes nylon as the active hard requirement.
- Reset clears conversation-specific state and initializes the named session using its supplied profile. The contract does not guarantee that every new session represents a different human user, so isolation follows the session boundary.

## My conclusion

The user understands confidence by provenance, preference supersession, and reset isolation. The user requested completion; no state representation or storage architecture was selected.

## Open questions

Ambiguous revisions, expiry of low-confidence beliefs, and evidence-preserving history compression remain unresolved. No state representation was selected.

## Evidence and sources

Ground competition facts in official repository documentation. Label conceptual state examples and method comparisons as teaching material rather than official requirements. Do not inspect application or evaluator source, private artifacts, prior implementations, or previous results.
