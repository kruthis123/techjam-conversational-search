# M0 Implementation Readiness and Evidence Inventory

- Status: `Complete`
- Date: `2026-09-17`
- Roadmap milestone: `M0 — Implementation readiness and evidence inventory`
- Current phase: `ARCHITECTING`

## Outcome being prepared

Understand the repository, frozen inputs, starter boundary, evaluator entry point, runtime assumptions, and existing evidence well enough to prepare the first M1 ADRs and one small task without guessing.

This report records inspection evidence. The user approved the roadmap and M0 scope on `2026-09-17`. It does not approve an implementation task or authorize implementation.

## Authority and immutable boundaries

Read in project order:

- `docs/PROJECT_STATE.md`;
- `docs/IMPLEMENTATION_ROADMAP.md`;
- `docs/competition_specification.md`;
- `docs/agent_api_contract.json`;
- `docs/evaluation_config.json`;
- `docs/submission_rules.md`;
- relevant accepted system-design records, templates, and standards.

Confirmed boundaries:

- `data/public_set.jsonl`, the frozen catalog once supplied, evaluator behavior, public labels, and the official contract must not be modified to improve a result.
- `starter/agent.py` is the editable external Agent boundary.
- The evaluator imports `Agent` from `starter.agent` and invokes `reset(...)` followed by at most ten calls to `respond(...)` per session.
- Exact valid `parent_asin` values determine hits; only the first ten valid unique recommendations are scored.
- Network access may be unavailable during official scoring.
- Raw catalog fields remain the factual source of truth under `SDR-001`; derived claims must retain provenance.

No conflict was found among the official contract files for the M0/M1 scope.

## Repository inventory

### Available

- Official contract and evaluation documents.
- `data/public_set.jsonl` with 200 parseable sessions.
- `data/catalog.jsonl` with 50,000 parseable products and unique `parent_asin` identities.
- Editable weak BM25 starter in `starter/agent.py`.
- Deterministic evaluator in `evaluator/local_evaluator.py`.
- Three focused evaluator tests in `tests/test_evaluator.py`.
- Recorded weak-baseline aggregate metrics in `docs/baseline_results.json`.
- System-design records `SDR-001` through `SDR-012`.
- ADR and task templates plus testing, style, and review standards.

### Remaining implementation work

- No Python dependency or runtime manifest is present yet; accepted `ADR-002` assigns its creation to the first implementation task.
- The shell's default `python3` is Python 3.9.6, so accepted verification commands must explicitly use the pinned Python 3.12 runtime.
- The local catalog SHA-256 is recorded below, but the published `SHA256SUMS` file is not present in this checkout for an independent checksum comparison.

## Deterministic evidence

### Public-set inspection

Command:

```bash
python3 -c 'import json,collections,pathlib; rows=[json.loads(x) for x in pathlib.Path("data/public_set.jsonl").read_text().splitlines() if x.strip()]; print("rows",len(rows)); print("scenarios",dict(sorted(collections.Counter(r["scenario_type"] for r in rows).items()))); print("unique_sample_ids",len({r["sample_id"] for r in rows})); print("unique_targets",len({r["ground_truth"]["parent_asin"] for r in rows})); print("missing_required",sum(not all(k in r for k in ("sample_id","scenario_type","user_profile","ground_truth")) for r in rows))'
```

Observed:

```text
rows 200
scenarios {'boundary': 10, 'browsing': 80, 'buying': 80, 'intent_override': 30}
unique_sample_ids 200
unique_targets 200
missing_required 0
```

### Contract JSON validation

Command:

```bash
python3 -m json.tool docs/agent_api_contract.json >/dev/null
python3 -m json.tool docs/evaluation_config.json >/dev/null
```

Observed: both files parsed successfully.

### Focused existing tests

Command:

```bash
python3 -m unittest discover -s tests -v
```

Observed: `3` tests passed under Python `3.9.6` during initial inspection and again under the pinned Python `3.12.14` runtime after the user's decision.

This proves only the existing evaluator helpers covered by those tests. It does not prove that the starter or end-to-end evaluator runs.

### Local retrieval prerequisite

Command:

```bash
python3 -c 'import sqlite3; c=sqlite3.connect(":memory:"); c.execute("CREATE VIRTUAL TABLE probe USING fts5(body)"); print("sqlite",sqlite3.sqlite_version,"fts5","available")'
```

Observed: SQLite `3.51.0` with FTS5 available.

### Catalog shape and identity audit

Observed under Python 3.12:

```text
rows 50000
json_errors 0
unique_ids 50000
duplicate_ids 0
missing_or_invalid_ids 0
missing_fields {}
unexpected_fields {}
```

All records contain the same ten documented keys. Value types vary where preservation matters:

- `price`: 39,473 null, 10,410 float, 117 string;
- `store`: 49,686 string, 314 null;
- list and dictionary fields retain their documented container shapes.

The locally recorded catalog SHA-256 is:

```text
da979b05a68af864cb0dcf9ee6a81c010c7e66a57978ad286c7a2e005fc69a67
```

### End-to-end evaluator

Command:

```bash
python3.12 -m evaluator.local_evaluator --output /private/tmp/techjam-m0-evaluator-results.json
```

Observed: completed successfully over 200 sessions and exactly reproduced the recorded weak baseline: HitRate@10 `0.125`, MRR `0.068034`, MTTC `9.81`, efficiency `0.119`, and technical score `0.10671`.

## Unresolved-matter classification

| Matter | Classification | Reason and owner |
|---|---|---|
| Roadmap and M0 scope approval | Already decided | Approved by the user on `2026-09-17`. |
| Frozen catalog availability | Resolved prerequisite | The 50,000-row catalog is available and reproduces the recorded baseline. The local digest is recorded; independent comparison with the published checksum remains outside this report. |
| Supported Python version and dependency declaration | Accepted implementation decision | `ADR-002` pins Python 3.12 and assigns a minimal manifest to the first task. |
| Raw product boundary and derived-claim provenance shape | Accepted implementation decision | `ADR-003` preserves raw mappings and keeps future derived claims separate. |
| Facet schema, aliases, units, and compatibility rules | Experimental parameters | `SDR-012` explicitly leaves these evidence-dependent. They belong to later M1 tasks and the normalization audit, not M0. |
| Catalog file location `data/catalog.jsonl` | Already decided | README, starter, and evaluator consistently use this path. |
| Product identity `parent_asin` | Already decided | The official contract and `SDR-001` make this the authoritative scored identity. |
| Catalog/index persistence | Deferred implementation decision | M1 says decide it only if viable alternatives materially affect later work; the first loader task does not yet require it. |

## ADR plan

- `ADR-002`: accepted Python/runtime and dependency-declaration baseline.
- `ADR-003`: accepted boundary between preserved raw product evidence and separate derived claims.

No ADR is needed merely to restate `parent_asin`, the official catalog path, or the accepted requirement that raw fields remain factual truth.

## First-task status

The intended first M1 task is a narrow catalog-loading behavior: read the verified frozen JSONL, preserve each raw product record, establish unique `parent_asin` identity, and report malformed or duplicate records without performing normalization or indexing.

`TASK-001` is now drafted for user approval. It adds the minimal Python 3.12 manifest as supporting setup and implements only raw catalog loading, identity validation, and preservation. Normalization, claim provenance, indexing, and Agent integration remain explicit non-goals.

## M0 exit assessment

| Exit condition | Result |
|---|---|
| Required data and boundaries are located or precisely recorded as missing | `PASS` — catalog, evaluator, runtime, and source boundaries are located and audited. |
| No contract conflict is unresolved | `PASS` for M0/M1 scope. |
| First implementation ADRs and one M1 task can be drafted without guessing | `PASS` — `ADR-002` and `ADR-003` are accepted and `TASK-001` is drafted. |

M0 is complete. This does not approve `TASK-001` or change the phase.

## Next approval gate

1. Review and explicitly approve or revise `TASK-001`.
2. Explicitly approve the phase transition from `ARCHITECTING` to `IMPLEMENTING`.
3. Only then may one implementer create the manifest and catalog loader.

