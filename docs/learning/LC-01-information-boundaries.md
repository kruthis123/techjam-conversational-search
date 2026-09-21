# LC-01: What information exists?

- Status: `Complete`
- Completion: User requested completion on 2026-09-11 after teach-back and a follow-up check.
- Prerequisites: LC-00 (complete; numerical exercise skipped by user choice)
- Official requirement references: `docs/competition_specification.md`, `docs/agent_api_contract.json`, `docs/submission_rules.md`

## Why this small problem matters

Understand which information is available to the agent, which conclusions require inference, and which information must remain outside its runtime inputs.

## Questions to answer

1. Which catalog fields are visible, and which field identifies a scored product?
2. What arrives at reset and on each conversation turn?
3. What does the aggregate user profile contain, and what does it omit?
4. Which information is available for public development versus hidden during evaluation?
5. How do observed facts, inferred preferences, and unknown values differ?
6. What would constitute data leakage?

## Small experiment or exercise

Given a toy product, aggregate profile, and user message, label information as observed, inferred, unknown, or evaluator-only. Explain one inference that the visible information does not justify.

## My teach-back answers

User's answers, recorded from the conversation:

1. "average_rating is the average over ratings provided by all users for that product. average_prior_rating is the rating given by the user across different products that they have bought previously"
2. "Catalog: Lightweight Bag made of waterproof material, User message: I want a bag to use every day in a place where it rains a lot. Observed - bag, inferred - waterproof, unknown - weight preference"
3. "If the agent were supploed the label then it will lead to over fitting"

Tutor feedback (not additional user-authored answers):

- The product rating aggregate and the user's historical rating aggregate describe different things. Exact aggregation details, including whether all users are included, are not specified in the supplied contract.
- Waterproofing is an observed catalog claim about this bag, but an inferred customer preference based on rainy conditions. The user's weight preference remains unknown even when the catalog describes the bag as lightweight.
- Supplying the target label during prediction is data leakage: it exposes the answer. Overfitting is adapting too closely to development examples and failing to generalize; leakage can occur without training.

Follow-up question: If the catalog did not mention waterproofing, would the rainy-location request justify claiming that this bag is waterproof?

User's answer: "No, there is no other mention about the bag being suitable for rainy weather or water protection so no claim can be made on its behalf"

Tutor feedback: Missing waterproofing evidence means unknown, not waterproof or not waterproof.

## My conclusion

The user's follow-up establishes that a customer's need does not justify an unsupported claim about a product. Customer needs, catalog claims, and unknown attributes must be distinguished. The user requested completion; no architecture decision was made.

## Open questions

Catalog field completeness, value formatting, and the controlled preference-tag vocabulary remain unverified without focused data sample inspection. Exact rating aggregation details are not established by the inspected contract documents.

## Evidence and sources

Use official repository documents and only data samples needed for this card. Do not inspect prior implementations, private artifacts, or evaluator source.
