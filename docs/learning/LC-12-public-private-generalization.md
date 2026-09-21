# LC-12: How will public results predict private results?

- Status: `Complete`
- Completion: User requested completion on 2026-09-15 after teach-back and tutor feedback.
- Prerequisites: LC-00 through LC-11
- Official requirement references: `docs/competition_specification.md`, `docs/evaluation_config.json`, `docs/submission_rules.md`, `docs/PROBLEM_MAP.md`

## Why this small problem matters

Improvements measured repeatedly on the same labeled public sessions may reflect tuning to those examples rather than behavior that generalizes to the private evaluation set.

## Questions to answer

1. How should public sessions be separated for development, comparison, and final checking?
2. What does an ablation reveal that an aggregate score does not?
3. Why must results be inspected by scenario and error type?
4. How do leakage, repeated tuning, and selection bias make public performance optimistic?
5. What uncertainty should accompany metrics computed from a finite sample?
6. How can evidence support a design decision without choosing an architecture prematurely?

## Small experiment or exercise

Given several fictional experiment results, identify which comparison is fair, which leaks labels or tunes on the final check set, and which aggregate result hides a scenario regression. State what additional evidence you would request.

## My teach-back answers

User's answers, recorded from the conversation:

1. "Leakage exposes the label to the agent whereas overfitting tries to make the agent predict the correct label for maximum of the development session inputs leading to more memorization and less generalization"
2. "If not run on identical sessions then cannot confidently say what factor caused the increase/decrease in score"
3. "Because most of the training data may belong to a category for which the newer settings are favourable while the regressed dataset had limited entries in the training data"

Tutor feedback (not additional user-authored answers):

- Leakage directly exposes unavailable answer information. Overfitting adapts to development-set peculiarities and may involve memorization or subtler dataset-specific rules and thresholds.
- Identical sessions control session difficulty; changing only one factor is also required for a causal ablation.
- Larger scenario groups can dominate an aggregate improvement while smaller groups regress and have noisier estimates. "Public/development sessions" is more precise than "training data" because no training method was selected.

## My conclusion

The user understands leakage versus overfitting, fair paired comparisons, and how aggregate gains can conceal scenario regressions. The user requested completion; no evaluation split, tuning process, or architecture was selected.

## Open questions

Internal split sizes, holdout viewing frequency, minimum scenario evidence, and confidence estimation remain unresolved. No evaluation process was selected.

## Evidence and sources

Ground competition facts in official repository documentation. Label statistical examples, split policies, and proposed diagnostics as teaching material rather than organizer requirements. Do not inspect application or evaluator source, private artifacts, prior implementations, or previous results.
