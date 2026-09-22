# M2 experiment: Inspect deterministic intent and session state

## Decision owner

The user runs and interprets this experiment. Codex has verified the implementation but must not choose the final interpretation rules.

## What was implemented

- `starter/intent.py` recognizes only the repository simulator's message templates and bare replies linked to a prior `ask_attribute`.
- It creates observed claims with `required`, `preferred`, or `indifferent` stance.
- `starter/session_state.py` keeps raw turn history, the question answered by each reply, current active claims, and unresolved turns separately for each session.
- Intent override removes earlier preferred claims but preserves required category claims.
- Reset replaces only the named session's state.

No Agent integration, general NLP, inference, summary, persistence, search state, or semantic event log exists.

## Run the fixed traces

From the repository root, run:

```bash
python3.12 - <<'PY'
from starter.session_state import SessionStateStore

store = SessionStateStore()

store.reset("reply")
store.receive("reply", 1, "I'm looking for hiking shoes, but I'm still exploring.")
store.record_ask_attribute("reply", "material")
print("ATTRIBUTE REPLY")
print(store.receive("reply", 2, "For that, what matters is: nylon."))

store.reset("boundary")
store.receive("boundary", 1, "I'm looking for dresses, but I'm still exploring.")
store.record_ask_attribute("boundary", "color")
print("\nINDIFFERENCE")
print(store.receive(
    "boundary",
    2,
    "I don't have a preference for color; please use your judgment.",
))

store.reset("override")
store.receive("override", 1, "I'm looking for handbags. leather")
print("\nOVERRIDE")
print(store.receive(
    "override",
    3,
    "Actually, ignore my earlier preference. What I need is: nylon.",
))

print("\nUNRESOLVED")
print(store.receive("override", 4, "Show me something different."))

print("\nRESET")
print(store.reset("override"))
PY
```

Then read:

1. `starter/intent.py`
2. `starter/session_state.py`

## Questions to answer

1. **Attribute reply:** Should `For that, what matters is: nylon.` remain `preferred`, or should it become `required` even though the user did not explicitly say `must`?
2. **Indifference:** Should a no-preference reply remove earlier claims for that attribute and leave one `indifferent` claim?
3. **Override:** Should `ignore my earlier preference` remove the active preferred claim while preserving unrelated required claims such as category?
4. **Unresolved message:** Should an unknown unlinked message remain in raw/unresolved history without changing active intent?

## Decision to report

Reply with:

```text
Attribute reply: preferred / required
Indifference: keep current behavior / change
Override: keep current behavior / change
Unresolved message: keep current behavior / change
Reasoning: ...
```

M2 remains open until these choices are recorded. After M2 is complete, Codex will commit all current changes and push `develop` before M3 begins.

## User result

Recorded on `2026-09-22`:

- Attribute reply: keep `preferred`.
- Indifference: remove any current claim for the attribute and add one indifferent claim. More generally, active intent must contain at most one claim per attribute.
- Override: replace only the claim for the changed attribute; do not remove unrelated preferred claims.
- Unresolved message: when it consumed a turn, retain it as unresolved history without changing active intent.

The pre-experiment implementation already handled indifference and unresolved turns this way. It could store multiple ordinary claims for one attribute and override removed every preferred claim, so `TASK-006` corrected those two behaviors. The focused correction and full suite passed, and final review found no remaining issue. M2 is complete.
