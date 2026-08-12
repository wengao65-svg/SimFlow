# MCP Server Design

## Role

MCP is the narrow runtime boundary for durable project truth and risky
execution. Scientific reasoning and ordinary file work remain with the host
agent and Skills.

## Public Surface

```text
simflow_state: inspect, record, checkpoint, recover
hpc:           plan, transfer, submit, status
```

Do not add a new public tool when an existing composite operation can own the
behavior internally. In particular, do not reintroduce separate state-read
prerequisites, workflow status/readiness variants, artifact/lineage registries,
activity lifecycle calls, handoff tools, or separate upload/download tools.

## State Tool Rules

- `inspect` is always read-only and must work for an uninitialized project.
- hosts perform at most one initial `inspect` per project per user request and
  reuse its Experiment selection context;
- `record` has a strict operational `kind` branch and a separate discriminated
  `channel="experiment"` branch with four entry types;
- `record` appends one logical operational event or one scientific notebook
  entry and refreshes the derived summary;
- `checkpoint` creates only a compact recovery reference.
- `recover` validates references and never executes or restores snapshots.
- every project operation receives explicit `project_root`;
- write schemas use `additionalProperties: false` at their public boundary;
- path references stay inside the project unless explicitly represented as
  metadata-only external sources;
- sensitive values are sanitized before persistence.

Experiment notebooks own scientific semantics; project files own exact
evidence. `records.jsonl` owns plan, approval, transfer, submit, status, and
checkpoint truth. Experiment/Attempt binding may be attached to operational
records, but it is excluded from immutable execution identity.

## HPC Tool Rules

- `plan` owns script preparation, dry-run validation, credential scanning, and
  immutable identity construction;
- `transfer` owns upload/download and manifest verification declared by the
  plan;
- `submit` accepts only `run_plan_hash` plus approval reference and bounded
  execution options;
- `status` reports connector state without claiming scientific success.

Approval binds the complete plan identity. Mutable submit-time script or input
hash fields are intentionally absent. Transfer and submit write one compact run
record automatically.

## Credential Boundary

The Agent-facing HPC server never receives private keys or an SSH agent socket.
Real SSH operations are delegated to the owner-only Unix-socket broker, which
accepts bounded structured operations and confines local paths to configured
roots. Missing or unsafe broker configuration fails closed.

## Host Adaptation

Standard MCP `clientInfo` changes discovery wording only. Tool semantics,
project-root checks, approval binding, and credential isolation are identical
for Codex, Claude Code, OpenCode, and generic clients. SimFlow does not need
skill-load telemetry or host transcript access.
