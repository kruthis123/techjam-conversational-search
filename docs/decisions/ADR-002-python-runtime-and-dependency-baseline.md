# ADR-002: Python runtime and dependency baseline

- Status: `Accepted`
- Author: `User`
- Date: `2026-09-17`
- Decision area: `M0 implementation readiness`
- Related learning cards: `LC-13`
- Related system-design records: `SDR-009`, `SDR-011`, `SDR-012`
- Official requirement references: `docs/submission_rules.md`, `README.md`

## Decision question

Which Python runtime range and dependency-declaration approach will all implementation tasks and verification commands use?

## Scope and non-goals

In scope:

- minimum or exact supported Python version;
- how the runtime and dependencies are declared reproducibly;
- the command form used by task verification;
- the default policy for adding dependencies.

Not decided here:

- application module layout;
- catalog, claim, retrieval, or ranking representations;
- deployment infrastructure;
- model or embedding dependencies that belong to later milestones.

## Contract facts and existing decisions

Facts:

- The README recommends Python 3.10 or later.
- Submission rules require the exact Python version requirement when non-default, dependency installation steps, and one reproduction command.
- Official scoring may disable network access.
- The weak starter currently uses only the Python standard library.
- The current shell resolves `python3` to Python 3.9.6 and also provides `python3.12` as Python 3.12.14.
- No runtime or dependency manifest is currently present.

Accepted design constraints:

- Keep the learning implementation simple and dependencies justified.
- Report operational failures rather than adding production-style runtime recovery.

User decision:

- pin the learning implementation to Python 3.12;
- create a minimal runtime and dependency manifest with the first implementation task.

## Inputs, outputs, ownership, and invariants

Input: repository source and declared dependencies.

Output: a reproducible local environment and exact task verification commands.

Invariants:

- a task must not claim verification under a runtime that was not used;
- dependencies must be declared before source relies on them;
- official evaluation must not require undeclared network services;
- adding a dependency requires a task-local reason.

## Failure cases

- development passes on Python 3.12 but uses features unavailable under a declared Python 3.10 minimum;
- commands accidentally use the shell's Python 3.9.6;
- a dependency works locally but is absent from submission instructions;
- an evaluator run requires a download unavailable during scoring;
- a lock or manifest is treated as reproducibility evidence without a matching executed command.

## What I need to research

- Questions I must answer:
  - Is this learning implementation intended to target one known local runtime or remain portable across Python 3.10+?
  - Should a manifest be created now or only when the first external dependency is approved?
- Sources or evidence needed:
  - local runtime inventory;
  - official submission reproducibility rules;
  - future dependency requirements as each milestone is prepared.

## Decision criteria

- reproducible commands;
- compatibility with the official recommendation;
- low setup and maintenance cost;
- no accidental reliance on unavailable network access;
- clarity about which runtime produced each piece of evidence.

## Options I considered

| Option | How it works | Strengths | Failure modes and trade-offs | Evidence |
|---|---|---|---|---|
| Pin Python 3.12 for the learning implementation and declare it immediately | Verification always runs through the available Python 3.12 runtime; add a minimal runtime manifest before implementation | Strong local reproducibility; avoids accidental Python 3.9 execution; one concrete command | Less portable than a range; official runner compatibility must be confirmed before submission | Python 3.12.14 is locally available; official requirement permits 3.10+ |
| Support Python 3.10+ and test against a defined compatibility set | Source avoids newer syntax and tasks identify the runtimes used | Broader compatibility with the project recommendation | More verification work; local environment currently lacks a discovered Python 3.10/3.11 executable; evidence may drift if only 3.12 is actually run | README recommends 3.10+ |
| Defer runtime declaration until an external dependency appears | Continue using whichever `python3` is active | No immediate setup document | Verification becomes ambiguous; current `python3` is below the recommended version; tasks cannot provide one stable command | Current runtime inventory shows the ambiguity |

## Validation experiments

No performance experiment is needed. Validation is deterministic:

- execute the focused test command through the selected runtime;
- inspect that the declared version matches the executed version;
- later run the evaluator through the same command once the catalog is available.

## Questions I must answer before deciding

Resolved by the user on `2026-09-17`:

1. Pin the locally available Python 3.12 runtime rather than promise untested Python 3.10+ compatibility.
2. Create the minimal project/runtime manifest with the first implementation task.

## My proposed decision

Use Python 3.12 for implementation and verification. Add a minimal `pyproject.toml` declaring `requires-python = ">=3.12,<3.13"` and an initially empty runtime dependency list. Use explicit `python3.12` commands until a later accepted task introduces a justified environment runner or external dependency.

## Architecture critic feedback

Not requested. This implementation decision does not change the conceptual agent.

## My final decision

Accepted by the user on `2026-09-17`:

- Python 3.12 is the pinned learning runtime.
- The first implementation task will add the minimal runtime/dependency manifest.
- The baseline starts with no external runtime dependencies.
- Verification commands name `python3.12` explicitly.

## Why I chose it and evidence used

- Python 3.12.14 is available locally and satisfies the official recommendation of Python 3.10 or later.
- The default `python3` resolves to Python 3.9.6, so explicit pinning prevents ambiguous evidence.
- The current starter and evaluator run with the standard library, so an empty initial dependency list is sufficient.
- Submission rules require reproducible setup and runtime disclosure.

## Rejected alternatives and why

- Python 3.10+ compatibility was rejected because the repository does not currently verify multiple supported runtimes.
- Deferring the runtime declaration was rejected because it would leave task commands dependent on an ambiguous shell default.
- A lock file is deferred while there are no external dependencies; introduce one only when an accepted task adds dependencies and can verify it.

## Consequences and trade-offs I accept

- The learning implementation is intentionally less portable than a tested Python 3.10+ range.
- Every implementation task must verify with Python 3.12.
- An approved dependency must be declared before source uses it.
- Official-runner constraints may require revisiting the pin before submission.

## Interfaces or invariants this decision creates

- `pyproject.toml` is the runtime and dependency declaration.
- `requires-python` remains within Python 3.12.
- The initial runtime dependency list is empty.
- Exact verification commands invoke `python3.12`.

## Compatibility check

- Official contract: any option must preserve the required Agent interface.
- Submission rules: runtime and dependency setup must be reproducible and documented.
- Existing SDRs: no conceptual capability is changed.
- Operational failure: version or dependency mismatch must be reported as a failed run.

## Revisit trigger

Revisit if the official runner constrains Python differently or an approved dependency cannot support the accepted runtime.
