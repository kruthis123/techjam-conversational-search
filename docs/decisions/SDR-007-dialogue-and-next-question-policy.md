# SDR-007: Dialogue and next-question policy

- Status: `Synthesized`
- Author: `User`
- Date: `2026-09-17`
- System-design area: `SD-07`
- Related learning cards: `LC-02`, `LC-08`
- Case-study references: `docs/competition_specification.md`, `docs/agent_api_contract.json`, `docs/evaluation_config.json`

## System question

How should the agent decide whether to recommend, ask a question, or do both, and how should it select an `ask_attribute` whose answer is likely to improve later candidate selection or ranking?

## Why this capability matters

Recommendations create the opportunity for an immediate hit. A useful question can reveal information that improves later turns, while an unanswerable or decision-irrelevant question consumes part of the ten-turn interaction and may steer the deterministic simulator down an unhelpful path. The API permits a natural-language message, one structured `ask_attribute`, and recommendations in the same response, so asking and recommending are not mutually exclusive.

This capability chooses the dialogue action and requested attribute. It does not reinterpret the reply, which returns through `SD-02` and `SD-03`, or independently alter the ranked list produced by `SD-06`.

## Information available

- current active intent, including known, unknown, indifferent, inferred, and unresolved attributes;
- confirmed and provisional candidates plus per-constraint uncertainty from `SD-05`;
- ranked candidates, score evidence, and near-ties from `SD-06`;
- catalog attribute coverage and value distribution among plausible candidates;
- attributes already asked and the resulting replies;
- current turn and remaining turn budget;
- the allowed `ask_attribute` vocabulary from the API contract;
- empty-set and ambiguity signals from upstream capabilities.

The hidden target, private intent card, and exact future simulator reply are unavailable.

## Useful representations

A question candidate may include:

- attribute name and allowed API value;
- current user-state status: unknown, unresolved, inferred, preferred, required, excluded, or indifferent;
- catalog coverage among retained candidates;
- candidate-value distribution and missing-value rate;
- plausible answer classes, including no preference or unavailable information;
- predicted candidate eliminations, eligibility changes, or rank movements per answer;
- whether the attribute was already asked;
- estimated information value, turn cost, and confidence;
- a reason for asking or declining to ask.

A dialogue action can be represented as recommend only, ask only, recommend and ask, report no suitable match, or request permission to relax a requirement.

## Solution families to learn

- fixed scripts or attribute order;
- rule-based gating using uncertainty, answerability, candidate coverage, and repeated-question checks;
- entropy or information-gain question selection;
- expected candidate reduction or expected rank-improvement selection;
- value-of-information policies that include turn cost and possible no-preference replies;
- decision trees or supervised action prediction;
- contextual bandits or reinforcement learning over multi-turn outcomes;
- adaptive stopping rules for asking versus recommending;
- recovery dialogue for empty, provisional-only, or conflicting candidate sets.

## What I need to research

- Concepts and vocabulary: clarification, slot or attribute question, answerability, information gain, entropy, expected value of information, candidate reduction, rank sensitivity, turn cost, stopping policy, exploration, exploitation, and repeated-question avoidance.
- Algorithms or system patterns: uncertainty rules, decision-tree policies, expected rank improvement, active feature acquisition, contextual bandits, and finite-horizon dialogue policies.
- Questions the research must answer:
  - When does asking provide value beyond recommending the current top products?
  - Should the agent normally recommend while asking, or ever withhold recommendations?
  - Which candidate and catalog statistics indicate that an attribute answer will be actionable?
  - How should no preference, unknown, or unanswerable replies affect expected question value?
  - How should repeated questions and already indifferent attributes be prevented?
  - How should the policy behave with only provisional candidates or no non-contradictory candidates?
  - What evidence would justify moving from deterministic rules to a learned dialogue policy?

## Comparison criteria

- HitRate@10, MRR, and mean turn to conversion;
- immediate-hit opportunity preserved or lost;
- fraction of questions whose answers change candidate eligibility or ranking;
- target-rank improvement after an answer;
- repeated, unanswerable, or no-effect question rate;
- behavior after no-preference replies and intent overrides;
- scenario-specific results, especially Buying versus Browsing;
- latency, token cost, explainability, reproducibility, and data requirements.

## Worked example or thought experiment

The user wants an everyday laptop bag and prefers blue. The top candidates differ as follows:

| Candidate | Laptop fit | Color | Current rank |
|---|---|---|---:|
| A | 15-inch | black | 1 |
| B | 13-inch | blue | 2 |
| C | unknown | blue | 3 |
| D | 15-inch | blue | 4 |

Color is already a known soft preference. Laptop size remains unknown and could change eligibility or ordering. Asking about laptop size is therefore potentially more actionable than repeating a color question. The agent could still recommend its current list in the same response.

## Learning experiment

Hold retrieval, constraint selection, and ranking fixed. Replay identical sessions under:

1. recommend-only;
2. always ask and recommend;
3. rule-gated asking based on unknown user attributes and catalog coverage;
4. expected candidate-change or expected rank-change question selection.

Measure core evaluator metrics, useful-question rate, target-rank movement, repeated-question rate, and outcomes by turn and scenario. Record each counterfactual answer branch where the deterministic simulator permits it. Introduce learned dialogue policies only if transparent rules fail on a named multi-turn decision pattern.

## My synthesis

### User's initial direction

1. When valid candidates and a useful question are available, always recommend and ask in the same turn rather than withholding recommendations.
2. Begin with a transparent rule-based question policy using catalog coverage, candidate disagreement, and expected eligibility or rank change.
3. When only provisional candidates remain because evidence is unknown, recommend those candidates while asking a useful question rather than withholding the recommendations.
4. Consider only unknown, inferred, or unresolved user attributes as question candidates. Exclude attributes already established as confirmed, required, preferred, excluded, acceptable, or indifferent.
5. Estimate question value using average-case impact across plausible answer branches. Until a justified probability model exists, treat the plausible branches equally rather than pretending their likelihoods are known.
6. Among eligible questions with positive average impact, ask the highest-value attribute without imposing an additional minimum-value threshold.
7. Combine expected candidate-eligibility changes, expected reduction in provisional or unknown assessments, and expected changes within the top ten when estimating impact. Give top-ten changes the highest priority.
8. Treat an answered attribute as resolved to a concrete stance or indifference and do not ask it again. Under the deterministic simulator scope, an attribute that remains unresolved after asking indicates an interpretation or extraction failure and should be surfaced for investigation rather than automatically repeated.
9. When no confirmed or provisional candidates remain, report that no suitable match was found. Do not ask to relax a hard requirement. Surface this unexpected state for offline investigation.
10. On the final turn, recommend only and set `ask_attribute = null` because no later turn can use the answer.
11. On earlier turns, compare question value relative to the other eligible questions for that same turn. Do not use one hard-coded question-value score or threshold across different turns; the candidate set, uncertainty, ranking, and available attributes are recomputed each turn.
12. For an unresolved user interpretation, ask an allowed `ask_attribute` only when that attribute passes the selected question-value policy. Otherwise ignore the unresolved update for current decision-making, leave the prior active intent unchanged, and retain the evidence for offline investigation.
13. Use the preserved structured question-reply link to interpret bare replies and prevent asking an answered attribute again.

### Facilitator refinement

- "Recommend and ask always" applies when a question passes the usefulness rules. If every attribute is already known or indifferent, catalog coverage is inadequate, plausible answers would not change the decision, or the question would repeat an answered attribute, use `ask_attribute = null` rather than manufacturing a question.
- Recommending provisional candidates does not convert unknown evidence into a supported product claim. The response and later explanation must preserve that uncertainty.
- Under the case-study output scope, inclusion of a provisional product means only that it is a plausible non-contradictory candidate. It does not assert that all requirements are confirmed.
- Expected impact is estimated by simulating plausible answer branches through the already selected constraint and ranking policies, then measuring changes in eligibility and rank. The initial policy uses an equal average and no additional threshold beyond positive value.
- Catalog coverage and candidate disagreement act as eligibility gates before average impact is compared. An attribute with unusable catalog coverage or no meaningful variation is not a useful question even if a noisy estimate is slightly positive.
- Include no-preference or indifference as a plausible answer branch where the simulator permits it. If that branch does not change current eligibility or ranking, it appropriately reduces the average immediate value of the question.
- Asking every positive-value question can make the policy sensitive to numerical noise. Revisit the absence of a threshold if selected questions repeatedly have negligible observed effect.
- Because the hidden target is unavailable at runtime, expected top-ten impact uses observable changes to the retained top-ten composition, ordering, score separation, and uncertainty rather than target-rank improvement.
- A no-suitable-match state may still arise from retrieval truncation, incomplete catalog evidence, or an upstream defect even if the simulator language is deterministic. Investigation should trace retrieval, fusion, constraint assessments, and current intent before changing dialogue policy.

No cross-turn question-value calibration is selected. The within-turn policy chooses the highest-value eligible attribute, while the final-turn rule prevents asking when the answer cannot be used.

## Connections to the rest of the agent

- Information required from upstream capabilities: active intent from `SD-03`, candidate uncertainty from `SD-05`, ranked candidates and score margins from `SD-06`, and catalog attribute coverage from `SD-01`.
- Information supplied to downstream capabilities: the chosen dialogue action, `ask_attribute`, rationale, and the recommendation list to be expressed by `SD-10`.
- New questions created for later areas: how profile information changes question value, when orchestration changes dialogue strategy, and how responses explain uncertainty without unsupported claims.

## Architecture critic feedback

Awaiting user synthesis.

## Revisit conditions

Revisit when questions frequently have no effect, repeat known information, delay hits, fail to recover provisional or empty candidate states, or require a multi-turn strategy not captured by deterministic rules.
