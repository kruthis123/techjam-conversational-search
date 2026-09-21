# LC-04: How can a large catalog produce candidates?

- Status: `Complete`
- Completion: User requested completion on 2026-09-13 after teach-back and tutor feedback.
- Prerequisites: LC-00, LC-01, LC-02, LC-03
- Official requirement references: `docs/competition_specification.md`, `docs/agent_api_contract.json`, `docs/evaluation_config.json`, `docs/PROBLEM_MAP.md`

## Why this small problem matters

Understand how catalog products become candidates for a request, why a target may be missed, and how candidate coverage differs from final recommendation quality.

## Questions to answer

1. What are the conceptual inputs and outputs of candidate retrieval?
2. How do exact, lexical, structured, semantic, graph/taxonomy, and hybrid methods find products?
3. What can each family miss, and what evidence does it depend on?
4. How do candidate coverage, candidate count, and processing cost interact?
5. How does target presence in an internal candidate set differ from official HitRate@10?
6. How could a fair comparison measure coverage and failure modes without choosing an architecture?

## Small experiment or exercise

Use a fictional bag query and a small catalog to explain which products different retrieval methods might find or miss. Identify an example of wording mismatch, unsupported exclusion, and semantic similarity without a required feature.

## My teach-back answers

User's answers, recorded from the conversation:

1. "Lexical retrieval relies on keyword match. A does not have the same keyword \"laptop bag\". B has the same but is not meeting the material requirement which is ignored by lexical retrieval"
2. "Blue is a soft preference so it should not be given higher priority over definite requirements that are fulfilled by C"
3. "Re-ranking strategy"

Tutor feedback (not additional user-authored answers):

- Plain lexical matching may miss A because its catalog uses different wording, while B may score well through word overlap despite violating the nylon requirement. Whether a lexical system also uses structured evidence depends on its design.
- Missing color evidence does not justify excluding C for a soft preference; its color remains unknown.
- If candidate coverage improves while final top-ten results worsen, inspect downstream ranking: distractor competition, hard-versus-soft weighting, score combination, and whether the target remains below the scored cutoff.

## My conclusion

The user understands wording mismatch, the danger of enforcing soft preferences, and the distinction between retrieval coverage and final ranking quality. The user requested completion; no architecture or retrieval method was selected.

## Open questions

Catalog completeness, category usefulness, complementary coverage, candidate budget, and acceptable retrieval cost remain unresolved. Specific ranking behavior will be studied in LC-06.

## Evidence and sources

Ground competition facts in official repository documentation. Label conceptual method comparisons and fictional results as teaching examples rather than measured findings. Do not inspect application or evaluator source, private artifacts, prior implementations, or previous results.
