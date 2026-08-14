# State And Recovery

## Compact Store

New SimFlow state separates scientific memory from operational truth:

```text
.simflow/
├── experiments/
│   ├── <experiment_id>.md
│   └── index.md
├── project.json
├── records.jsonl
├── checkpoints/
└── reports/
```

- Experiment Markdown files are append-only scientific notebooks.
- `records.jsonl` is the append-only operational event history.
- `project.json` and `experiments/index.md` are derived summaries.
- `checkpoints/` stores compact recovery references.
- `reports/` stores migration, transfer, run-plan, and requested human-readable
  reports.

`inspect` is read-only and does not create this tree. The first `record` or
`checkpoint` creates only the compact paths required by that operation.

## Project Summary

The summary tracks:

- current goal;
- active run ID;
- latest milestone, failure, and checkpoint;
- next action;
- total and per-kind record counts;
- last record metadata.

It is deterministically rebuilt from Experiment notebooks, operational records,
and checkpoint references. Incremental updates are only a cache optimization;
deleting a valid `project.json` must not lose project truth.

## Experiment Notebooks

One Experiment represents one scientific question. Parameter axes such as
temperature, element, seed, retry, and resume belong to Attempts unless they
change the question or acceptance criteria.

Notebook entry types are limited to `experiment`, `attempt`, `observation`, and
`decision`. This is the Experiment Memory v1 ontology ceiling: Experiment is
the question, Attempt is a scientific strategy, Observation is what was seen,
and Decision is what follows. Notebook files own scientific semantics; actual
project files own exact evidence. A path/hash reference identifies evidence
content but does not establish completion, convergence, or scientific validity.

The public `record` input uses a discriminated contract. Existing operational
calls keep the operational `kind` schema. `channel="experiment"` uses a separate
`entry_type` schema and cannot fall back to operational kinds or a generic note.

An Attempt is not a Run. One Attempt may reference multiple training,
validation, retry, or resume Runs. Operational execution does not create an
Attempt.

## Logical Records

Operational record kinds are:

```text
milestone  run  artifact  analysis  evidence_change  approval  failure  note
checkpoint  recovery  migration
```

The public `record` tool writes the first eight plus explicit migration
confirmation. Checkpoint and recovery records are written by their runtime
operations.

`evidence_change` is one immutable fact event for a completed, partial, or
failed filter, delete, overwrite, replacement, deduplication, move, or other
persistent evidence change. It has no planned/open/terminal/reverted or
recoverability lifecycle. Plans belong to approvals or run plans. A later undo
is another `evidence_change` linked to the earlier event with `parent_ids`.

One record represents one logical event or deliverable. Related files belong in
the record's `artifacts` references or a manifest. `parent_ids` express useful
provenance. Do not create records for every transient log, plot attempt, cache,
or helper call.

Records sanitize bearer tokens, secret assignments, private-key material, and
sensitive fields such as password, token, API key, private-key, and POTCAR body
content.

## Recovery Checkpoints

A checkpoint may contain:

- `record_id`, `run_id`, or `milestone_id`;
- the current records byte offset;
- input and restart file references with hashes;
- resume command;
- risk notes;
- `ready`, `partial`, or `diagnostic` status.

It never contains state, artifact, lineage, gate, or job registry snapshots.
A recoverable checkpoint requires at least one real recovery reference.
Diagnostic checkpoints may document a failure boundary but are not runnable.

`recover` validates that referenced paths remain inside the project, still
exist, and match recorded hashes. It returns readiness and instructions; it
does not execute the resume command or roll project files backward.

## Legacy Compatibility

Historical projects may contain:

```text
.simflow/state/*.json
.simflow/memory/**/*
<nested project path>/.simflow/
```

Compact runtime treats these as read-only. Compatibility Python APIs may list
legacy artifacts and checkpoints, but new writes do not synchronize old
registries. Legacy snapshot checkpoints are never restored into active state.

With `include_legacy=true`, `inspect` inventories structured state JSON, legacy
memory files, and nested roots. The inventory contains relative paths, sizes,
SHA-256 hashes, safe JSON/JSONL shape/counts, SQLite header metadata, and safety
declarations. It never queries SQLite tables and does not include state or
memory field values, host transcripts, or scientific result files.

Migration requires explicit confirmation of the exact current report hash. It
persists one migration report and one compact record. Source files remain
byte-identical. A changed source invalidates the old hash.

## Root Boundary

`project_root` is the user project and the only authorized SimFlow write root.
`plugin_root` is only the installed code location. MCP cwd must never be used as
the project root.

`.omx/`, Codex/Claude/OpenCode session files, and other host state are outside
SimFlow ownership. They are not copied, deleted, or imported.
