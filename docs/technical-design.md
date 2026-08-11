# SimFlow Technical Design

## Four-Layer Model

```text
Host Agent
  reasoning, search, coding, tools
       |
Research Task Skill
  literature, proposal, modeling, computation, analysis, writing
       | optional
Domain Skill
  VASP, CP2K, LAMMPS, GPUMD/NEP, MLP
       |
SimFlow Runtime
  inspect, compact records, approval, execution truth, recovery
       |
.simflow/
```

The two Skill layers answer how to work reliably. Runtime answers what happened
and what must be safeguarded. Stages and directories do not select Skills, and
Skill selection does not imply a runtime write.

## Event Flow

1. Route the immediate user intent to zero or one Task Skill and zero or one
   Domain Skill.
2. Perform the scientific work with host tools and optional helpers.
3. Use runtime only if a meaningful event needs durable provenance, approval,
   execution truth, or recovery.
4. Append one compact record for the logical event rather than synchronizing
   multiple registries.
5. Create a compact checkpoint only when restart or recovery information has
   real value.
6. For real execution, build an immutable run plan, obtain approval for its
   hash, then transfer/submit/status through the bounded HPC surface.

## State Model

```text
.simflow/
├── project.json              # Derived current summary
├── records.jsonl             # Append-only logical events
├── checkpoints/              # Compact recovery references
└── reports/                  # Migration, HPC, and requested reports
```

`project.json` tracks the current goal, active run, latest milestone, latest
failure, latest checkpoint, next action, counts, and last record. A record may
reference project-relative files, hashes, parent record IDs, and structured
details. Credentials and restricted file bodies are sanitized before writing.

Historical `.simflow/state/*.json` registries are compatibility inputs only.
They are not updated by compact writes. Migration inventories structured state
paths, sizes, hashes, and JSON shape without importing transcripts or
scientific data content.

## Runtime Surfaces

`simflow_state` exposes `inspect`, `record`, `checkpoint`, and `recover`.
`hpc` exposes `plan`, `transfer`, `submit`, and `status`.

The public surface deliberately omits state-read prerequisites, stage update
tools, artifact/lineage registries, experiment/activity lifecycle calls,
session handoff calls, and separate upload/download tools.

## Helpers And Compatibility

`runtime/simflow_helpers/` contains optional scientific utilities and internal
delivery/verification adapters. Helpers remain usable without SimFlow state.
Legacy Python APIs may read old projects or map old calls to compact records,
but they are not public MCP tools and must not recreate synchronized state
registries.

## Hard Boundaries

- explicit `project_root` for project operations;
- one root `.simflow/` and no automatic nested-root migration;
- writes confined to the authorized project;
- no credentials or restricted bodies in persisted records;
- no real execution without approval bound to the current `run_plan_hash`;
- no claim that submission, parsing, or file presence proves successful or
  scientifically valid completion;
- no automatic project layout reorganization.
