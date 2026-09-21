# SDR-002: User intent and constraint understanding

- Status: `Synthesized`
- Author: `User`
- Date: `2026-09-16`
- System-design area: `SD-02`
- Related learning cards: `LC-01`, `LC-03`
- Case-study references: `docs/competition_specification.md`, `docs/agent_api_contract.json`

## System question

How can a user's message become a grounded representation of product need, hard constraints, soft preferences, negation, indifference, ambiguity, and inferred intent without inventing certainty?

## Why this capability matters

Catalog representations describe products; intent understanding describes what the user currently wants. Retrieval, constraint checking, ranking, dialogue policy, personalization, and explanation all depend on these two sides being alignable. An early meaning error can propagate through the entire agent.

## Information available

Potential evidence includes:

- the current raw user message;
- earlier conversation messages and current conversational state, studied more deeply in `SD-03`;
- aggregate profile information, whose influence is studied in `SD-08`;
- the catalog vocabulary, normalized facets, and taxonomy learned in `SD-01`;
- the absence of information, which must remain unknown rather than becoming a preference.

Current-message evidence, conversation-derived evidence, profile priors, and catalog-driven inference must remain distinguishable.

## Useful representations

Conceptual information to preserve:

- product need or candidate categories;
- use case and goal;
- attribute, value, and comparison operator;
- requirement strength: hard, soft, acceptable, indifferent, or unknown;
- polarity and negation scope;
- whether information adds, replaces, removes, or contradicts earlier intent;
- supporting message span or paraphrase;
- observed versus inferred provenance;
- confidence and unresolved ambiguity;
- candidate clarification when multiple interpretations remain plausible.

The final representation is not yet selected. The purpose of this list is to identify meaning that downstream capabilities may need.

## Solution families to learn

- deterministic patterns, dictionaries, and catalog-aware normalization;
- intent classification and slot or entity extraction;
- sequence labeling and joint intent/slot models;
- semantic parsing into a structured intent frame;
- LLM-based structured extraction;
- retrieval- or taxonomy-grounded interpretation;
- hybrid systems combining extraction, normalization, validation, and clarification;
- uncertainty-preserving approaches that return multiple interpretations instead of forcing one.

## What I need to research

- Concepts and vocabulary: intent, slot, entity, semantic frame, dialogue act, negation scope, modality, preference strength, coreference, uncertainty, calibration, ontology grounding.
- Algorithms or system patterns: rules, classifiers, sequence labeling, semantic parsing, structured LLM extraction, constrained decoding, candidate generation and validation, clarification under ambiguity.
- Sources: primary work on joint intent classification and slot filling, schema-guided dialogue, semantic parsing, and evaluated LLM information extraction.
- Questions the research must answer:
  - Which meanings require explicit representation rather than free-text summaries?
  - How should explicit evidence differ from plausible inference?
  - How should hard requirements, soft preferences, acceptable alternatives, indifference, and unknowns differ?
  - How can catalog vocabulary help normalize intent without making unsupported assumptions?
  - When should ambiguity produce multiple hypotheses or a clarification question?

## Comparison criteria

To be confirmed by the user. Candidate criteria include semantic accuracy, negation and scope handling, unseen-value generalization, grounding and provenance, uncertainty preservation, consistency across paraphrases, data requirements, explainability, latency, cost, and adaptability to new product domains.

## Study sequence

1. Model a message as a turn-level intent delta rather than one intent label or the complete conversation state.
2. Compare free-text summaries, fixed slot frames, open claim lists, and hybrid intent representations.
3. Compare rules, supervised intent/slot extraction, schema-guided models, LLM structured extraction, and hybrid grounded interpretation.
4. Use contrast sets for modality, negation, correction, indifference, ambiguity, and unseen attributes.
5. Record the user's conceptual intent representation and staged understanding strategy.

## Research evidence

- Joint intent classification and slot filling shows the traditional utterance-level intent plus token-level slot framing: https://arxiv.org/abs/1902.10909
- Schema-guided dialogue research studies natural-language schema descriptions as a way to extend beyond fixed slot labels: https://aclanthology.org/2021.naacl-main.62/
- Schema-driven prompting demonstrates generative state extraction conditioned on slot descriptions: https://aclanthology.org/2021.emnlp-main.404/
- Multi-intent research highlights that real utterances can contain several simultaneous intents rather than one label: https://arxiv.org/abs/2108.11711

## Worked example or thought experiment

Message: "I need a backpack for commuting. I preferred leather—actually, no leather. Nylon is fine, it must fit a 15-inch laptop, and I don't care about color."

Meanings to examine:

- product need: backpack;
- use case: commuting;
- leather: earlier preference explicitly cancelled and replaced by negative evidence;
- nylon: acceptable, but not necessarily required or preferred;
- laptop fit: hard 15-inch requirement;
- color: explicit indifference;
- remaining attributes: unknown unless established elsewhere.

The exercise will compare which solution families preserve these distinctions and which collapse them.

### User's first exercise answers

1. "Observed - backpack, no leather, for 15 inch laptop. Inferred - lightweight"
2. "leather - excluded, nylon - acceptable, laptop size - required, color - indifferent"
3. "Open claim list - it should store attributes and their observation like required, preferred, excluded, indifferent etc"

### Facilitator feedback

- Backpack, commuting, no leather, nylon being acceptable, the 15-inch laptop requirement, and color indifference are all directly expressed in the message. Lightweight has no supporting evidence and must remain unknown; "inferred" does not permit adding a plausible but unsupported preference.
- The strength classifications for leather, nylon, laptop size, and color are correct.
- An open claim list preserves multiple values and strengths better than a simple slot frame. To support downstream use, each claim also needs its value or relation, polarity or strength, supporting message evidence, observed-versus-inferred provenance, confidence or ambiguity where relevant, and whether it adds, cancels, or replaces meaning. This remains a conceptual information model, not a code schema.

### User's initial understanding strategy

1. Observed-claim extraction and inference should be separate conceptual capabilities.
2. An attribute absent from the known catalog schema should first be mapped to known concepts and, when necessary, trigger clarification.
3. Begin with a grounded hybrid understood as deterministic plus supervised interpretation, and consider adding an LLM later if performance is poor.

### Facilitator refinement

- "Grounded hybrid" is a pattern rather than one fixed combination. It can combine any candidate extractor with evidence attachment, catalog or ontology normalization, validation, uncertainty preservation, and clarification. The user's deterministic-plus-supervised starting combination is one valid form when suitable labelled data exists.
- An out-of-schema claim should retain its original wording and evidence while attempting normalization. If several mappings remain plausible, the system should preserve those alternatives rather than forcing one known concept; the dialogue policy can later decide whether clarification is worth a turn.
- Poor aggregate performance is not by itself evidence that an LLM is the missing capability. Paraphrase or unseen-attribute failures may justify testing an LLM; normalization failures point toward catalog vocabulary or ontology work; negation and strength failures may require better contrast data or explicit safeguards; conversation-update failures belong to `SD-03`.
- LLM introduction should therefore be a targeted ablation against a named error slice, with unsupported-claim rate measured alongside extraction coverage.

### User's refinement questions and choices

1. The user proposed using an LLM initially to convert the fixed unstructured product catalog into labelled data.
2. The user agreed that inferred claims may influence retrieval, ranking, and clarification but not create hard exclusions, and asked how inference could be generated without an LLM.
3. The user selected paraphrase misses and complex corrections as the error slices that would trigger an LLM experiment.

### Facilitator clarification

- LLM-assisted catalog labelling can create normalized product attributes or weak labels, but it does not directly create labelled conversational intent data. Catalog text teaches product evidence; user-message data must teach claim strength, negation, correction, indifference, and update operations.
- The fixed catalog can define attribute and value vocabulary. An LLM can extract product claims with source spans and provenance, and those weak labels can support catalog representations. A held-out, independently checked sample is still needed because training and evaluating on the same LLM-generated labels would reproduce the annotator's mistakes.
- Conversational training data can be created separately through human-labelled messages, deterministic contrast templates, LLM-generated paraphrases and corrections, or combinations. Synthetic examples must be tested against an independently authored contrast set.
- Inference does not require an LLM. It can arise from explicit rules, taxonomy or ontology relationships, similarity to previously labelled examples, supervised classifiers, probabilistic associations, or graph relations. In every case, the supporting evidence, confidence, and intended downstream use must remain explicit.
- Paraphrase misses and complex corrections are appropriate slices for testing an LLM candidate-claim generator. The comparison must also measure unsupported claims and incorrect strength or negation, not only added coverage.

### Open synthetic-conversation data strategy

The user proposed running the repository's deterministic simulator, capturing its customer messages, using an LLM to generate related messages for other catalog products, and training on both original and generated messages.

Repository documentation confirms that a deterministic local evaluator can be run and writes per-session results, but the local `data/catalog.jsonl` required by the evaluator is not currently present. The documented output does not guarantee the exact transcript fields, so transcript availability must be verified by running the approved experiment rather than inspecting evaluator source during ARCHITECTING.

System-design refinement:

- Simulator transcripts can provide seed dialogue patterns, scenario structure, and examples of replies to `ask_attribute`.
- Repeated deterministic runs may reproduce the same language unless the probing policy asks different attributes or follows different trajectories.
- Training only on simulator language risks learning simulator phrasing rather than general conversational intent.
- Synthetic generation should begin from a structured intent frame whose attributes, strengths, negations, and update operations are the labels. The LLM paraphrases that frame into natural language; it should not freely invent a message and then label its own invention.
- Product metadata used to construct an intent frame must not leak unique title phrases, target identity, or unsupported properties into generated messages.
- Original and synthetic examples can both be training data, but evaluation must use independently authored or checked messages, preferably split by product and linguistic template before generation.
- Contrast sets should explicitly cover paraphrases, complex corrections, negation scope, preference strength, indifference, and out-of-schema claims.

### User-defined closed-world evaluation scope

The user chose to evaluate this project only against the repository's deterministic simulator and its existing language templates. LLM paraphrasing is not required for the current project.

Consequences of this scope:

- Simulator-generated messages and replies may be used directly as conversational training data.
- Training coverage should vary products, attribute values, scenario types, turns, and `ask_attribute` trajectories while preserving the simulator's language templates.
- Train, validation, and test partitions should be separated by products or structured intent frames before collecting examples, rather than randomly splitting near-identical templated messages.
- A deterministic or template-aware interpreter becomes a valid baseline. A supervised model may still be trained, but success on the same templates primarily demonstrates value and scenario generalization within a closed grammar, not robustness to natural paraphrases.
- The previously proposed LLM trigger for paraphrase misses is outside the current project scope. Complex corrections remain relevant only in the forms generated by the simulator.
- Any later claim of general conversational understanding would require reopening this assumption and adding independently authored or paraphrased evaluation messages.

This scope does not change the use of an LLM for offline product-catalog attribute extraction; that is a separate product-side representation task.

## Learning experiment

Generate simulator conversations separately over product- or intent-frame-disjoint training, validation, and test partitions. Evaluate a deterministic interpreter first on:

- product need and attribute-value extraction;
- requirement, preference, acceptable, excluded, indifferent, and unknown status;
- negation scope;
- correction and replacement operations;
- exact supporting message evidence;
- unsupported-claim rate;
- complete turn-level claim-frame accuracy.

Classify errors before adding another extraction family. Test supervised or LLM-based extraction only against the specific slices that deterministic interpretation cannot cover. This experiment requires the missing local catalog and explicit user approval before execution.

## My synthesis

Accepted by the user on `2026-09-16`:

- Represent each turn as an open list of claims rather than one intent label or a fixed slot-only frame.
- Preserve attribute or relation, value, stance or strength, polarity, supporting message evidence, observed-versus-inferred provenance, uncertainty, and whether the turn adds, cancels, or replaces meaning.
- Keep observed-claim extraction separate from inference. Inferred claims may expand retrieval, weakly influence ranking, or motivate clarification, but may not create hard exclusions.
- Attempt to normalize unfamiliar user expressions onto catalog concepts while retaining the original expression and alternative mappings. Ambiguous, decision-relevant mappings remain available for later clarification.
- Use an LLM offline to propose structured product attributes from the fixed catalog when useful, while retaining raw catalog fields as truth and marking implicit values as inferred. Product-side labels do not substitute for conversational labels.
- Evaluate this project only against the repository's deterministic simulator and its existing language templates. LLM paraphrasing and general natural-language robustness are outside the current scope.
- Generate conversational data by running simulator trajectories across varied products, scenarios, turns, and `ask_attribute` choices. Partition by product or structured intent frame before collection to avoid near-duplicate leakage.
- Begin with a robust deterministic interpreter grounded in simulator templates and catalog vocabulary.
- Add supervised or LLM-based extraction only when error analysis identifies a specific deterministic coverage gap. Aggregate poor performance alone is not a sufficient trigger.
- Complex simulator correction patterns are a candidate trigger. Paraphrase misses are not relevant under the current closed-world scope.
- The mechanism for generating optional inferred claims remains open and separate from observed extraction; rules, ontology relations, similarity, supervised models, or graphs may be compared when inference is needed.

No implementation technology or model has been selected.

## Connections to the rest of the agent

- Information required from upstream capabilities: raw messages, conversation context, catalog vocabulary, and provenance-aware product concepts.
- Information supplied to downstream capabilities: grounded intent hypotheses, constraints and preferences with strength, uncertainty, and evidence.
- New questions created for later areas: how intent changes are merged across turns, how retrieval consumes multiple hypotheses, and when dialogue policy should ask for clarification.

## Architecture critic feedback

Awaiting user synthesis.

## Revisit conditions

Revisit when later memory, retrieval, constraint, ranking, or dialogue choices require intent information not represented here.
