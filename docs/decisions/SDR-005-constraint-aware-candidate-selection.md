# SDR-005: Constraint-aware candidate selection

- Status: `Synthesized`
- Author: `User`
- Date: `2026-09-17`
- System-design area: `SD-05`
- Related learning cards: `LC-03`, `LC-05`, `LC-09`
- Case-study references: `docs/competition_specification.md`, `docs/evaluation_config.json`

## System question

How should the agent compare retrieved products against active user constraints, distinguish confirmed matches from contradictions and missing evidence, and reduce the candidate pool without falsely excluding plausible products?

## Why this capability matters

Retrieval in `SD-04` deliberately favors recall and may return partial matches, semantic neighbors, and products with incomplete metadata. Constraint-aware selection determines which candidates are demonstrably incompatible, which are confirmed to satisfy requirements, and which remain uncertain. A false exclusion here cannot be repaired by later ranking.

This capability validates product evidence against active constraints. It does not decide the final order among retained products; that belongs to `SD-06`.

## Information available

- the current active intent, including requirement, exclusion, preference, indifference, unknown, and unresolved states;
- retrieved product identities and retrieval-route evidence from `SD-04`;
- raw catalog fields and normalized facets from `SD-01`;
- claim-level provenance indicating observed, normalized, inferred, ambiguous, or missing product information;
- categorical, numeric, range, set-membership, compatibility, and descriptive constraints;
- the raw message evidence behind each active user claim.

The hidden target and private intent card are unavailable. Retrieval similarity is not proof that a product satisfies a requirement.

## Useful representations

A candidate-by-constraint assessment can preserve, for each pair:

- the active user constraint and its strength;
- the relevant catalog value or absence of value;
- normalized comparison values and units;
- assessment state: confirmed match, confirmed contradiction, unknown, ambiguous, or unresolved;
- supporting catalog evidence and provenance;
- comparison confidence and any normalization uncertainty;
- the resulting candidate status and reason.

This representation keeps missing evidence distinct from negative evidence and makes exclusion decisions traceable.

## Solution families to learn

- confirmed-match-only filtering, which retains only products proving every requirement;
- contradiction-only filtering, which removes only products proven incompatible and retains unknowns;
- tiered eligibility, such as confirmed eligible, provisionally eligible, and ineligible;
- confidence-threshold policies for normalized or inferred product facts;
- deterministic comparators for categorical, numeric, range, set, and compatibility constraints;
- conflict-aware or abstaining comparison when evidence is ambiguous;
- constraint relaxation, fallback, or clarification when too few candidates survive;
- rule-based versus learned product-constraint matching.

## What I need to research

- Concepts and vocabulary: hard constraint, exclusion, entailment, contradiction, unknown, open-world versus closed-world assumptions, three-valued logic, abstention, constraint satisfaction, unit normalization, compatibility, provenance, confidence, false exclusion, and relaxation.
- Algorithms or system patterns: deterministic typed comparators, compatibility tables, tiered eligibility, confidence thresholds, selective classification, and constraint-relaxation policies.
- Questions the research must answer:
  - What evidence is strong enough to confirm or contradict each type of requirement?
  - Should products with unknown attributes survive, be demoted, or trigger clarification?
  - Can inferred product claims ever confirm a hard requirement, or only keep a candidate plausible?
  - How should multiple hard constraints combine when some match and others are unknown?
  - How should conflicting catalog evidence be represented?
  - Who may relax a hard requirement, and under what evidence or user authorization?

## Comparison criteria

- target survival after constraint processing;
- false-exclusion rate and contradiction leakage rate;
- coverage of categorical, numeric, range, compatibility, and negated constraints;
- treatment of missing, ambiguous, and inferred metadata;
- traceability of each decision to catalog and user evidence;
- retained candidate count and downstream ranking cost;
- latency, rule-maintenance cost, and evaluation difficulty;
- behavior by Buying, Browsing, Intent Override, and Boundary slices.

## Worked example or thought experiment

Active requirements: `material = nylon only`, `fits 15-inch laptop`, and `price <= $80`.

| Candidate | Catalog evidence | Per-constraint assessment |
|---|---|---|
| A | nylon; 15-inch sleeve; $72 | all confirmed matches |
| B | polyester; 16-inch sleeve; $60 | material contradiction; other constraints match |
| C | material missing; 15-inch sleeve; $70 | material unknown; other constraints match |
| D | nylon; 13-inch sleeve; $55 | laptop-size contradiction; other constraints match |
| E | inferred nylon; 15-inch sleeve; $75 | material support is inferred rather than confirmed |

The exercise is to decide which products are ineligible, confirmed eligible, or provisionally eligible without allowing matching attributes to compensate for a hard contradiction.

## Learning experiment

Create a fixed candidate-by-constraint table covering exact matches, contradictions, missing values, inferred values, ambiguous normalization, numeric boundaries, and multiple simultaneous requirements. Compare confirmed-match-only filtering, contradiction-only filtering, and tiered eligibility.

Measure target survival, contradiction leakage, retained candidate count, and failure slices. Keep the incoming retrieval pool fixed so retrieval changes cannot explain the result.

## My synthesis

### User's initial direction

1. Use tiered eligibility for the worked example:
   - A is confirmed eligible.
   - C and E are provisionally eligible because C has missing material evidence and E has only inferred material support.
   - B is ineligible when material is a hard requirement because polyester contradicts nylon.
   - D is ineligible when laptop fit is a hard requirement because its 13-inch capacity contradicts the 15-inch requirement.
2. Treat inferred matching evidence as somewhat stronger than completely unknown evidence while keeping both below confirmed catalog evidence.
3. Leave the response to an empty eligible set open for later experimentation, including whether any constraint relaxation is useful.
4. Require observed or otherwise reliable catalog evidence for a confirmed contradiction and exclusion; inferred evidence alone is insufficient.
5. Combine hard-constraint assessments using this rule:
   - any confirmed contradiction makes the candidate ineligible;
   - no contradictions and confirmation of every requirement makes it confirmed eligible;
   - no contradictions but at least one unknown, inferred, ambiguous, or unresolved assessment makes it provisionally eligible.
6. When no confirmed candidate remains, retain candidates with unknown attributes as provisional candidates. Do not automatically relax the hard requirement.
7. Treat deterministic unit conversions and accepted catalog aliases as confirmed evidence when the normalized value remains traceable to the raw catalog source.
8. When reliable catalog fields conflict about a required attribute, classify the relevant assessment as ambiguous and the candidate as provisional unless another confirmed contradiction makes it ineligible. Surface the catalog conflict for offline investigation.
9. If deeper retrieval yields only confirmed contradictions and no provisional candidates, leave the runtime response open between asking permission to relax and reporting no suitable match. Do not silently relax the requirement.
10. Treat a product described only as water-resistant as unknown or insufficiently supported for a waterproof requirement, not as a confirmed contradiction. The weaker statement does not prove the stronger property or its absence unless the controlled catalog vocabulary explicitly defines them as equivalent.
11. Interpret an unqualified `no leather` exclusion across product components: confirmed leather trim is a confirmed contradiction even when the main body uses another material.
12. Allow reliable dimensional evidence to establish compatibility without requiring an explicit compatibility sentence. The dimensions must describe the relevant usable space, use compatible units and orientation, and satisfy any required clearance; unrelated or external product dimensions are insufficient.
13. A provisional product is a plausible candidate whose available evidence does not contain a confirmed contradiction; it is not a claim that every hard requirement is known to be satisfied.

### Facilitator refinement

- The worked example explicitly defines material, laptop fit, and budget as active requirements, so B and D have confirmed hard contradictions rather than merely conditional mismatches.
- Inferred support and unknown evidence can form different provisional tiers or later ranking signals, but inferred support does not become a confirmed fact merely because it is stronger than no evidence.
- Experiments can compare recovery actions when no confirmed candidate survives. They cannot by themselves authorize silently violating an explicit hard requirement. Candidate recovery, asking the user for permission to relax, and recommending a known contradiction are semantically different actions and must be evaluated separately.

### Facilitator update after the second decision round

- The evidence threshold, multi-constraint aggregation, and first empty-set recovery action are now selected.
- Reliable deterministic normalization may support confirmation when it preserves the raw catalog meaning and remains traceable to it. Unsupported inference remains provisional.
- If neither confirmed nor provisional candidates remain, asking the user to revise a requirement remains conceptually distinct from silently relaxing it.
- The deterministic simulator reduces ambiguity in user claims but does not guarantee that the post-fusion candidate pool has complete, non-conflicting catalog evidence. Empty-set recovery therefore remains a real system case even if it is expected to be rare.

`SD-07` later resolves the empty-set response to reporting no suitable match without relaxing the requirement. The relative ordering of confirmed and provisional candidates is owned by `SD-06` ranking.

## Connections to the rest of the agent

- Information required from upstream capabilities: active constraints and evidence from `SD-02` and `SD-03`, catalog facts and provenance from `SD-01`, and the fused candidate pool from `SD-04`.
- Information supplied to downstream capabilities: retained candidates with per-constraint match, contradiction, and uncertainty evidence plus explicit exclusion reasons.
- New questions created for later areas: how confirmed and provisional candidates should be ranked, when uncertainty should trigger a question, and when orchestration may invoke fallback or relaxation.

## Architecture critic feedback

Awaiting user synthesis.

## Revisit conditions

Revisit when ranking, dialogue, or evaluation reveals false exclusions, excessive contradiction leakage, too many unresolved candidates, unsupported compatibility assumptions, or unacceptable comparison cost.
