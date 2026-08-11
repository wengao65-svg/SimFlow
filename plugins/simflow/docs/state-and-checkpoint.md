# State And Recovery

## Compact Store

New SimFlow state uses four concepts:

```text
.simflow/
├── project.json
├── records.jsonl
├── checkpoints/
└── reports/
```

- `project.json` is a derived current summary.
- `records.jsonl` is the append-only logical event history.
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

It is derived from compact records and is not a second authoritative event
history.

## Logical Records

Record kinds are:

```text
milestone  run  artifact  analysis  approval  failure  note
checkpoint  recovery  migration
```

The public `record` tool writes the first seven plus explicit migration
confirmation. Checkpoint and recovery records are written by their runtime
operations.

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
<nested project path>/.simflow/
```

Compact runtime treats these as read-only. Compatibility Python APIs may list
legacy artifacts and checkpoints, but new writes do not synchronize old
registries. Legacy snapshot checkpoints are never restored into active state.

With `include_legacy=true`, `inspect` inventories only structured state JSON and
nested roots. The inventory contains relative paths, sizes, SHA-256 hashes, JSON
shape/counts, and safety declarations. It does not include state field values,
host transcripts, or scientific result files.

Migration requires explicit confirmation of the exact current report hash. It
persists one migration report and one compact record. Source files remain
byte-identical. A changed source invalidates the old hash.

## Root Boundary

`project_root` is the user project and the only authorized SimFlow write root.
`plugin_root` is only the installed code location. MCP cwd must never be used as
the project root.

`.omx/`, Codex/Claude/OpenCode session files, and other host state are outside
SimFlow ownership. They are not copied, deleted, or imported.
