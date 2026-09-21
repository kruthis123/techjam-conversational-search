# User Coding Style

This file is intentionally sparse. It becomes the durable coding lens only through user-approved examples.

## Initial principles

- Prefer simple, human-readable code over cleverness.
- Keep modules focused and dependencies justified.
- Implement only approved behavior; avoid speculative abstractions.
- Preserve clear names and explicit control flow.

## User-approved rules

### Learning-first minimal implementation

- Rule: Implement the smallest clear behavior needed for the current learning experiment. Prefer short, explicit code and task-specific data structures. Do not add abstractions, fields, validation, fallback behavior, or edge-case handling until the contract, fixed data, or an observed experiment failure requires them.
- Why it matters: The user wants to read and understand every implemented file, learn one concept at a time, and compare alternatives through their own experiments rather than receive a production-hardened system.
- Accepted example: A small price function that returns one simple source-linked price claim for the numeric values present in the fixed catalog and otherwise abstains.
- Counterexample: A generic claim framework with relation, unit, evidence, component, serialization, and exhaustive malformed-input handling before more than one claim family needs those concepts.
- Date approved: `2026-09-18`

### Evidence-led complexity

- Rule: Treat unimplemented edge cases and alternative designs as explicit limitations or experiment candidates, not automatic coding requirements. Add complexity only after a focused experiment or observed failure shows why it is needed.
- Why it matters: Evaluating alternatives is itself a learning goal.
- Accepted example: Record that lower-bound string prices are deferred, measure their frequency, and compare a parser later only if they affect a target experiment.
- Counterexample: Parse every imaginable currency, range, malformed number, and locale before the baseline behavior has been measured.
- Date approved: `2026-09-18`

### Autonomous implementation, user-owned experiments

- Rule: Once the user asks to implement a named roadmap milestone, Codex chooses the simplest bounded implementation details and completes the coding without asking the user to decide routine technical matters. Codex must stop at the milestone experiment checkpoint, explain the implementation, provide exact experiment instructions, and leave the comparison and keep/change/defer decision to the user.
- Why it matters: The user wants to learn by reading a small implementation and personally evaluating alternatives, not by making every coding decision or receiving a production-oriented system.
- Accepted example: Codex chooses a short deterministic parser consistent with the simulator grammar, tests it, explains it, and then gives the user fixed message traces for comparing its behavior.
- Counterexample: Codex asks the user to select classes and libraries before coding, or independently runs a retrieval comparison and silently adopts the winning configuration.
- Date approved: `2026-09-18`

## Topics still to learn from feedback

- Naming
- Function and module size
- Data models and typing
- Error handling
- Logging and observability
- Comments and documentation
- Dependency policy
