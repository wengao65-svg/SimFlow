# Target Repository Structure

## Source Layout

```text
simflow/
├── skills/                    # 12 public Skills, kept flat for host discovery
├── workflow/
│   ├── stages/                # Advisory research-intent contracts
│   ├── recipes/               # Optional reference paths
│   ├── gates/                 # Evidence and approval definitions
│   ├── policies/              # Runtime safety and recording contracts
│   └── toolchains/            # Helper support metadata
├── mcp/
│   ├── servers/simflow_state/ # inspect, record, checkpoint, recover
│   ├── servers/hpc/           # plan, transfer, submit, status
│   └── shared/
├── runtime/
│   ├── simflow_core/          # Compact records, gates, migration, compatibility
│   └── simflow_helpers/       # Optional scientific/internal helpers
├── schemas/
├── templates/
├── tests/
├── docs/
└── scripts/                   # Validation, packaging, and scaffolding
```

The flat `skills/<name>/SKILL.md` layout is retained because Codex, Claude Code,
and OpenCode distribution validators discover direct children. Logical Router,
Task, and Domain classification does not require a physical directory move.

## Public Skills

The only directories containing public `SKILL.md` files are the router, six
Research Task Skills, and five Domain Skills. Safety, checkpoint, handoff, and
verification implementations belong under runtime helpers. Unsupported engine
placeholders do not expose `SKILL.md`.

## Runtime

`runtime/simflow_core/records.py` owns the compact project store.
`migration.py` inventories legacy structured state without modifying it.
`gates.py` provides internal approval records. Compatibility modules may expose
old Python call shapes to existing code but must map new writes to compact
records or recovery references.

`runtime/simflow_helpers/delivery/` and `verification/` contain operational
implementations that are no longer public Skills. Engine and task helpers must
remain optional and usable without state.

## User State

New project runtime state is:

```text
.simflow/
├── project.json
├── records.jsonl
├── checkpoints/
└── reports/
```

Historical `.simflow/state/` remains read-only compatibility input. The source
repository ignores `.simflow/` because it is local runtime state.
