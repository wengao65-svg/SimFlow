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
  inspect, experiment notebooks, operational truth, approval, recovery
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
3. On the first SimFlow use for a project in a user request, inspect existing
   experiment context once without writing.
4. Persist scientific context in the relevant Experiment notebook and machine
   execution truth in operational records; never make both stores authoritative
   for the same field.
5. Create a compact checkpoint only when restart or recovery information has
   real value.
6. For real execution, build an immutable run plan, obtain approval for its
   hash, then transfer/submit/status through the bounded HPC surface.

## State Model

```text
.simflow/
├── experiments/
│   ├── <experiment_id>.md    # Canonical scientific memory
│   └── index.md              # Derived navigation
├── project.json              # Derived current summary
├── records.jsonl             # Canonical operational events
├── checkpoints/              # Compact recovery references
└── reports/                  # Migration, HPC, and requested reports
```

Each Experiment is defined by one scientific question. Temperature, element,
seed, retry, and resume variations are Attempts unless the scientific question,
acceptance criteria, or interpretation target changes. Notebook entries cover
experiment scope, attempt intent, observations, decisions, material evidence
changes, recovery decisions, uncertainty, and next action.

`records.jsonl` is authoritative for immutable plan, approval, transfer,
submission, scheduler status, and checkpoint events. Experiment and Attempt IDs
are binding metadata on those records and never participate in
`run_plan_hash`. Exact structures, trajectories, models, outputs, and logs remain
scientific evidence files; notebooks retain references and hashes, not copies.

`project.json` and `experiments/index.md` are rebuilt deterministic views over
both canonical stores and checkpoints. They are caches, not additional sources
of truth.

Historical `.simflow/state/*.json` registries and `.simflow/memory/` files are
compatibility inputs only. They are not updated by compact writes. Migration
inventories paths, sizes, hashes, safe JSON/JSONL shape, and SQLite header
metadata without querying tables or importing transcripts, memory values, or
scientific data content.

## Runtime Surfaces

`simflow_state` exposes `inspect`, `record`, `checkpoint`, and `recover`.
`hpc` exposes `plan`, `transfer`, `submit`, and `status`.

The public surface deliberately omits state-read prerequisites, stage update
tools, artifact/lineage registries, session contexts, activity lifecycle calls,
mandatory handoff calls, and separate upload/download tools. Experiment
notebooks are accessed through the existing composite state tools.

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
- no session/activity ledger, SQLite experiment database, or synchronized
  notebook exports;
- no experiment or attempt identifier in immutable execution identity.
