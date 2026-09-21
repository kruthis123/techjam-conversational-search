# SDR-010: Grounded response and explanation

- Status: `Synthesized`
- Author: `User`
- Date: `2026-09-17`
- System-design area: `SD-10`
- Related learning cards: `LC-01`, `LC-02`, `LC-14`
- Case-study references: `docs/competition_specification.md`, `docs/agent_api_contract.json`, `docs/submission_rules.md`

## System question

How should selected recommendations and dialogue actions become a natural, contract-valid response whose product claims are supported by catalog evidence and whose prose question agrees with the structured `ask_attribute`?

## Why this capability matters

Upstream capabilities decide intent, candidates, eligibility, order, and whether to ask. Response generation must communicate those decisions without inventing product attributes, strengthening provisional evidence, changing recommendation order, or asking a different question in prose. Although the evaluator scores identifiers rather than prose claims, grounded communication is required for a coherent and trustworthy agent.

## Information available

- the ordered recommendation list and ranking evidence from `SD-06`;
- confirmed and provisional assessments plus uncertainty from `SD-05`;
- the selected dialogue action and `ask_attribute` from `SD-07`;
- raw catalog fields and traceable normalized evidence from `SD-01`;
- current active intent from `SD-03`;
- technical-failure or empty-response state from `SD-09`;
- the public response schema and allowed `ask_attribute` values.

The generator does not know the hidden target, private intent card, or unsupported product facts. Similarity, inferred product views, profile tendencies, and user needs do not establish catalog claims.

## Useful representations

A response content plan may contain:

- ordered recommendation identifiers that generation cannot reorder or replace;
- supported claim candidates with product identity, attribute, value, raw source evidence, normalization provenance, and confidence state;
- claims prohibited because evidence is missing, inferred, conflicting, or irrelevant;
- the selected `ask_attribute` and a matching question intent;
- whether uncertainty must be disclosed for provisional products;
- response mode: normal recommendation, recommendation plus question, no suitable match, or technical containment;
- optional model-usage evidence.

The content plan is a grounding boundary between agent decisions and surface wording.

## Solution families to learn

- fixed templates populated only from structured evidence;
- deterministic evidence-to-text rules;
- retrieval-augmented generation from a bounded evidence packet;
- constrained LLM generation from an approved content plan;
- generate-then-verify approaches that reject unsupported claims;
- claim-level attribution or evidence linking;
- confidence-aware wording for provisional evidence;
- final response checks for schema, identifiers, order, duplication, prose-question alignment, and unsupported claims.

## What I need to research

- Concepts and vocabulary: grounding, attribution, entailment, hallucination, content planning, surface realization, provenance, uncertainty communication, faithful generation, and constrained decoding.
- Algorithms or system patterns: template generation, slot filling, evidence-conditioned generation, claim extraction and verification, natural-language inference checks, and structured output validation.
- Questions the research must answer:
  - Which product claims are safe to communicate as facts?
  - How should provisional, inferred, unknown, or conflicting evidence be worded?
  - Should every recommendation include a reason, or only the strongest supported evidence?
  - How can generation be prevented from changing recommendation identity or order?
  - How is prose kept consistent with `ask_attribute`, including `null`?
  - When does an LLM add enough language quality to justify verification, latency, and reproducibility costs?
  - What should the customer-facing message say for no-match and technical-containment responses?

## Comparison criteria

- unsupported-claim and contradicted-claim rate;
- claim coverage and usefulness;
- exact preservation of recommendation identifiers and order;
- prose and `ask_attribute` agreement;
- appropriate uncertainty expression;
- contract-valid response rate;
- consistency across repeated runs;
- latency, token cost, and dependency risk;
- customer readability and concision.

## Worked example or thought experiment

Current need: a bag for a rainy commute that fits a 15-inch laptop.

- Product A explicitly states `waterproof nylon shell` and `15-inch laptop sleeve`. Both claims may be stated as supported facts.
- Product B is semantically similar to rainy-commute products, but its catalog does not mention water protection. The response must not call it waterproof or water-resistant.
- Product C has inferred water resistance from a generated product view and confirmed laptop fit. The inferred property may support retrieval but cannot be presented as a confirmed catalog fact.

If `ask_attribute = "material"`, the prose may ask about material. If `ask_attribute = null`, it should not contain a question that expects the simulator to supply an attribute preference.

## Learning experiment

Create a fixed set of recommendation content plans containing confirmed, normalized, inferred, unknown, conflicting, no-match, and technical-failure cases. Compare:

1. deterministic templates;
2. evidence-conditioned generation if language quality remains inadequate;
3. generation with claim verification if an LLM is introduced.

Measure unsupported claims, omitted useful claims, uncertainty wording, identifier and order preservation, question-field agreement, response validity, latency, and repeatability. Do not allow language quality gains to compensate for grounding or contract regressions.

## My synthesis

### User's direction

1. Do not introduce natural-language response generation for this evaluator scope. The deterministic simulator uses the structured `ask_attribute` rather than interpreting the customer-facing prose.
2. Do not generate product explanations or disclose supporting, missing, inferred, or conflicting catalog evidence in `message`.
3. Do not generate per-product reasons or a summary explaining why the recommendation list was selected.
4. Assign automatic final contract validation to the response-emission boundary. It checks required fields, catalog-valid unique identifiers, preserved order, allowed `ask_attribute`, final-turn `null`, and usage shape when present.

### Facilitator refinement

- The public contract still requires `message` to be a string. Use a minimal deterministic placeholder or generic action-neutral message; no language model, evidence-to-text system, or claim verifier is justified.
- The ordered recommendation identifiers come directly from `SD-06`, and the structured `ask_attribute` comes directly from `SD-07`. Minimal response assembly must not reorder, replace, or invent identifiers or change the selected attribute.
- Because the message makes no product claims, unsupported-claim and uncertainty-disclosure risks are avoided rather than solved through generation.
- Contract validity, catalog-valid unique identifiers, order preservation, `ask_attribute` membership, final-turn `null`, and technical empty-response behavior still require verification even when prose is semantically unused.
- If automatic final validation fails, report the failed run and rerun after investigation; do not emit the invalid response or design a production recovery path for this learning project.
- This is a case-study scope decision, not a general conclusion that customer-facing recommendation agents do not need grounded explanations.

The exact placeholder string is an implementation detail. Revisit natural-language generation only if a later interface, human user, or evaluation criterion consumes the message content.

## Connections to the rest of the agent

- Information required from upstream capabilities: ordered products, claim-level evidence, uncertainty states, selected dialogue action, active intent, and failure mode from `SD-01` through `SD-09`.
- Information supplied to the external contract: customer-facing `message`, structured `ask_attribute`, ordered recommendation identifiers, and optional usage reporting.
- New questions created for later areas: how evaluation samples and scores groundedness, and how the final conceptual agent shows the response-grounding boundary.

## Architecture critic feedback

Awaiting user synthesis.

## Revisit conditions

Revisit when templates cannot express required cases clearly, generated language introduces unsupported claims or question mismatches, response validation fails, or grounding adds unacceptable latency.
