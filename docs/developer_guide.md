# SimFlow Developer Guide

## Design Rule

Keep scientific guidance, domain knowledge, and runtime state separate.

```text
current intent -> one Task Skill + optional Domain Skill
actual event   -> compact runtime record/recovery/safety operation
```

Do not add lifecycle calls merely to prove that a Skill was used.

## Skills

A Research Task or Domain Skill is a pure instruction bundle. It may guide,
inspect, suggest, and use host tools. It must not:

- require MCP or state initialization;
- own stage progression, approval, artifact registration, or checkpoints;
- enforce a fixed project layout, parser, helper, report, or software path;
- claim support for an engine that has no tested Domain Skill.

Keep high-frequency and high-risk behavior in `SKILL.md`; move long methods and
examples into `references/`. Public Skills remain direct children of `skills/`
until every host supports recursive discovery.

## Helpers

Helpers are optional scientific utilities. By default they read project files
and write requested outputs inside the authorized project without initializing
SimFlow state. Optional recording belongs in a shared adapter and should append
one logical record, not per-file registry updates.

Safety, delivery, and verification helpers are internal runtime modules, not
public Skills. Engine helpers must return uncertainty for unsupported tasks.

## Compact State

Use the canonical stores according to ownership:

- `experiment_notebook` for append-only scientific semantics;
- `record_event` for one logical event;
- `inspect_project` for read-only status;
- `create_recovery_checkpoint` for a real recovery boundary;
- `recover_checkpoint` for reference/hash validation.

`record` has two strict branches. Operational writes use `kind` and must reject
Experiment-only fields. Experiment writes use `channel="experiment"`, one of
the six entry types, and an entry-specific payload; they must reject `kind`.
Keep actual scientific files authoritative and rebuild `project.json` with
`rebuild_project_summary()` from notebooks, records, and checkpoints.

Do not add new writes to legacy `.simflow/state/*.json` registries. Legacy APIs
may read them and may provide compatibility views, but compact writes must not
synchronize artifact, lineage, stage, job, or checkpoint registries.

Legacy migration may inventory `.simflow/memory/` recursively, but it may emit
only path, size, hash, JSON/JSONL container shape, and SQLite header metadata.
It must never query SQLite tables, expose stored values, or alter source bytes.

## MCP

The public surface is fixed at four `simflow_state` and four `hpc` tools unless
a new product decision justifies expansion. Composite tools should expose
strict JSON schemas and explicit `project_root` where project access is needed.

Real execution must be derived from a persisted run plan and approval bound to
its `run_plan_hash`. Experiment and Attempt bindings belong to operational plan
records and must not participate in that hash. HPC may bind only existing
Experiment and Attempt references and must never create either. An Attempt is a
scientific strategy; a Run is one actual execution, and one Attempt may bind
multiple Runs. Submit inputs must not accept mutable replacement hashes.

Experiment Memory v1 has a fixed ontology ceiling of Experiment, Attempt,
Observation, and Decision. Do not add lifecycle entry types or a generic action
taxonomy. Persistent evidence changes are single immutable operational
`evidence_change` events and never expose planned/open/reverted state.

## Workflow Contracts

Stage and recipe files are guidance. Runtime policy files may enforce only real
safety, truth, recording, and recovery boundaries. Do not reintroduce automatic
stage-boundary checkpoints, per-file artifact versioning, mandatory phase
transitions, or directory admission rules.

## Validation

```bash
python -m pytest tests/ -q
npm run validate:all
python scripts/audit_skill_scripts.py
npm run validate:release -- --skip-wrapper-build
```

Changes to distribution content also require marketplace/package builds and
isolated host smoke tests from the release checklist.
