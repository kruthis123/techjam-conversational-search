# SDR-008: Personalization

- Status: `Synthesized`
- Author: `User`
- Date: `2026-09-17`
- System-design area: `SD-08`
- Related learning cards: `LC-01`, `LC-10`
- Case-study references: `docs/competition_specification.md`, `docs/agent_api_contract.json`

## System question

How should aggregate historical profile information influence retrieval, ranking, and dialogue without being mistaken for current intent, overriding explicit requests, or excluding a target for a different occasion or recipient?

## Why this capability matters

The current request may be vague, especially in Browsing sessions. Aggregate historical tendencies can provide a weak prior in those cases. The same tendencies can be misleading when the user shops for a different purpose, changes preference, or buys for someone else. Personalization must therefore add bounded evidence while preserving the authority of the current conversation.

## Information available

At session reset, the contract supplies:

- `purchase_frequency`;
- `average_prior_rating`;
- `rating_style`;
- controlled `preference_tags`;
- an aggregate `summary`.

The agent does not receive direct identifiers, purchase timestamps, free-text reviews, raw purchase histories, or the hidden target. Recency, recipient, occasion, item-level sequence, and causal reasons for past purchases are therefore unavailable.

## Useful representations

Keep profile evidence separate from active conversational intent. A profile signal may include:

- source profile field;
- normalized category, attribute, value, or behavioral tendency;
- relevance to the current product category or decision;
- support strength and uncertainty;
- whether the current conversation confirms, leaves open, or contradicts it;
- permitted downstream uses, such as retrieval expansion, bounded ranking prior, tie-breaking, or question prioritization;
- suppression reason when current evidence overrides it.

The representation must not label a historical tendency as a present requirement or observed product fact.

## Solution families to learn

- no-personalization baseline;
- profile use only as a final tie-breaker;
- bounded ranking boosts for relevant profile tendencies;
- retrieval expansion or route weighting based on profile terms without hard filtering;
- profile-informed question selection for attributes likely to matter;
- explicit relevance and conflict gates before any profile use;
- learned personalization or user embeddings;
- collaborative-filtering-style priors, where sufficient interaction data exists;
- adaptive suppression when current behavior repeatedly conflicts with profile tendencies.

## What I need to research

- Concepts and vocabulary: prior, current evidence, context relevance, preference drift, cold start, over-personalization, negative transfer, user embedding, collaborative filtering, popularity bias, filter bubble, and bounded influence.
- Algorithms or system patterns: tie-breaking priors, bounded boosts, relevance gates, conflict suppression, user-item models, contextual personalization, and ablation testing.
- Questions the research must answer:
  - What does each aggregate field establish, and what remains unknown?
  - Which current-request evidence must suppress a profile tendency?
  - How should category or use-case relevance be determined?
  - May profile evidence expand retrieval, influence ranking, prioritize a question, or all three?
  - How strong may profile influence become when current intent is vague?
  - How can personalization help without reducing target recall or diversity?
  - What evidence would justify a learned user representation from these limited aggregates?

## Comparison criteria

- target rank and HitRate@10 with profile off versus on;
- results for vague versus explicit current requests;
- relevant-category versus unrelated-category profile use;
- current-profile conflict and different-occasion slices;
- false exclusions and target suppression caused by profile evidence;
- marginal retrieval contribution and ranking movement;
- question usefulness changes;
- explainability, stability, latency, privacy exposure, and generalization.

## Worked example or thought experiment

Profile tendency: the user often buys casual silver jewellery and usually gives high ratings.

| Current request | Safe interpretation question |
|---|---|
| "Show me some jewellery." | Could the casual/silver tendency weakly break ties or guide a question? |
| "I need grand gold jewellery for a wedding." | The explicit occasion and material conflict with the historical tendency; profile influence must be suppressed. |
| "I need a backpack." | Jewellery history is unrelated and should not influence products. |

The exercise is to decide where profile evidence may enter the agent and how strongly it may act in each case.

## Learning experiment

Hold sessions, retrieval inputs, and candidate sets fixed where applicable. Compare:

1. profile ignored;
2. relevant profile used only as a final tie-breaker;
3. relevant profile used as a bounded ranking prior;
4. profile-assisted retrieval or question selection only if earlier variants expose a named gap.

Report core metrics and target movement for vague, explicit, profile-aligned, profile-conflicting, unrelated-category, and different-occasion slices. A profile variant fails if it improves aggregate results by suppressing targets on conflict slices.

## My synthesis

### User's initial direction

1. Ignore aggregate profile information in the initial agent. It does not influence retrieval, constraint selection, ranking, or question selection.
2. Introduce profile use later only when evaluation identifies a concrete opportunity, and add it at the capability where the opportunity occurs rather than enabling personalization globally.
3. For any later profile experiment, require relevance to the same product category and require the current request to be silent about the profiled attribute.
4. If current intent conflicts with one historical tendency, suppress only that profile attribute rather than disabling every unrelated profile signal for the session.
5. Require a repeated, named failure slice and a paired comparison against the no-profile baseline before introducing personalization.
6. If a future experiment is justified, begin with controlled `preference_tags`. Defer the free-form `summary`, `rating_style`, and `average_prior_rating` until a separate failure hypothesis establishes why those fields are relevant.
7. Treat no regression on profile-conflicting and unrelated-category sessions as a hard acceptance condition. Reject a personalization variant that improves aggregate metrics by harming either slice.

### Facilitator refinement

- A no-profile baseline provides the counterfactual needed to measure whether personalization actually helps rather than assuming that historical information has value.
- Ignoring the profile means it has no decision influence. The reset payload may remain available as separate raw input for a later approved experiment, but its tags or summary must not leak into query construction, ranking features, constraints, or dialogue decisions.
- A future opportunity should be classified by failure location: retrieval expansion addresses candidate omissions, a bounded ranking prior addresses ambiguity among retained candidates, and profile-informed questioning addresses an information-acquisition gap.
- Even in a relevant category, profile evidence remains historical. It cannot create hard filters, confirm current intent, or override an explicit current statement.

The exact future profile method remains intentionally unselected. Its capability location, influence strength, and evaluation are determined only after a qualifying failure slice is observed.

## Connections to the rest of the agent

- Information required from upstream capabilities: the reset profile, active current intent from `SD-03`, catalog concepts from `SD-01`, and current retrieval, ranking, and dialogue evidence.
- Information supplied to downstream capabilities: bounded profile priors with relevance, conflict, provenance, and suppression information.
- New questions created for later areas: when orchestration disables personalization, how explanations mention historical tendencies, and how evaluation detects over-personalization.

## Architecture critic feedback

Awaiting user synthesis.

## Revisit conditions

Revisit when personalization suppresses explicit current intent, reduces recall on conflict or different-occasion slices, adds no measurable value for vague requests, or available profile information proves too weak for reliable use.
