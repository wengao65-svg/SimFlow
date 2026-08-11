# MCP Tool Reference

SimFlow exposes two MCP servers and eight composite tools. Skills do not require
MCP engagement. Use these tools only when project truth, approval, transfer,
execution, or recovery needs runtime support.

## `simflow_state`

All state tools require explicit `project_root`.

### `inspect`

Read compact project status without writing.

Required:

- `project_root`

Optional filters:

- `kind`: `milestone`, `run`, `artifact`, `analysis`, `approval`, `failure`,
  `note`, `checkpoint`, `recovery`, or `migration`;
- `status`, `record_id`, `run_id`;
- `limit` from 1 to 200;
- `include_legacy`, default `true`.

The result includes the derived project summary, filtered recent records, and
record counts. With `include_legacy=true`, it also includes:

- a concise legacy-state presence summary;
- a read-only migration report covering `.simflow/state/*.json` and nested
  `.simflow` roots;
- `migration_report_hash` for explicit confirmation.

`inspect` does not initialize `.simflow`, update timestamps, import host
transcripts, or modify legacy files.

### `record`

Append one logical project event.

Required:

- `project_root`;
- `kind`;
- `summary`.

Ordinary record kinds are `milestone`, `run`, `artifact`, `analysis`,
`approval`, `failure`, and `note`. Optional fields include `status`, `stage`,
`run_id`, `goal`, `next_action`, `artifacts`, `parent_ids`, and `details`.

Use one record for a meaningful run or deliverable. `artifacts` are path/hash
references inside that logical record; they are not separate registry writes.
`parent_ids` provide event-level provenance. Sensitive values and restricted
file bodies are sanitized before persistence.

For an explicit legacy migration confirmation, use:

```json
{
  "project_root": "/path/to/project",
  "kind": "migration",
  "summary": "Index legacy SimFlow state",
  "confirm_migration": true,
  "migration_report_hash": "<exact hash returned by inspect>"
}
```

The current inventory must match the supplied hash. Repeating the same
confirmed hash is idempotent. Migration writes one report and one compact
record; it never moves, renames, deletes, or rewrites scientific data.

### `checkpoint`

Create a compact recovery reference.

Required:

- `project_root`;
- `summary`.

Optional:

- `status`: `ready`, `partial`, or `diagnostic`;
- `record_id`, `run_id`, `milestone_id`;
- `input_refs`, `restart_refs`;
- `resume_command`, `risk_notes`.

A `ready` or `partial` checkpoint requires at least one recovery reference.
Checkpoint files contain a records offset, references, hashes, restart paths,
and instructions. They do not copy state, artifact, lineage, gate, or job
registries. Ordinary task completion does not require a checkpoint.

### `recover`

Validate a compact checkpoint and return recovery readiness.

Required:

- `project_root`.

Optional:

- `checkpoint_id`; when omitted, the latest compact checkpoint from
  `project.json` is used.

`recover` checks referenced paths and hashes and returns the resume command. It
does not execute compute, restore a legacy snapshot, or modify project files.

## `hpc`

### `plan`

Prepare or validate a job and persist one immutable run plan.

Required:

- `project_root`;
- `script_path`;
- non-empty `input_paths`.

Optional fields include `scheduler`, SSH `target`, `remote_workdir`,
`manifest_path`, `base_dir`, `resources`, `destructive_scope`, bounded SLURM
`generate` fields, and a transfer declaration.

The resulting `run_plan_hash` covers script and input hashes, scheduler, target,
remote directory, resources, transfer scope, destructive scope, and restricted
file metadata. The plan performs dry-run validation and credential scanning.
Planning does not approve or execute the job.

### `transfer`

Execute the upload or download declared in an approved immutable run plan.

Required:

- `project_root`;
- `run_plan_hash`;
- `direction`: `upload` or `download`.

Also supply `gate_decision_id` or `approval_token` for an approval bound to the
same hash. Transfer parameters cannot replace the plan's paths, target, or
directories. SimFlow verifies source and destination manifests and records one
compact run event plus a transfer report.

### `submit`

Submit an unchanged approved run plan.

Required:

- `project_root`;
- `run_plan_hash`.

Also supply an approval reference. SSH submit additionally requires the
verified `transfer_manifest`; local execution may specify `timeout`.

Submit recomputes the plan identity. Any change to script, inputs, target,
remote directory, resources, transfer scope, destructive scope, or restricted
metadata returns `run_plan_stale` and requires new approval. An unchanged retry
may reuse the same approval. Every submit attempt records one compact run event.

### `status`

Read job status through the bounded connector abstraction.

Required:

- `job_id`.

Optional:

- `scheduler`;
- SSH `target` when `scheduler="ssh"`.

Status does not infer scientific convergence. A scheduler state and a
scientific result are separate facts.

## SSH And Restricted Files

SSH targets accept only `host` plus optional `user` and `port`. Passwords,
private keys, key paths, and arbitrary SSH options are rejected. Real SSH
operations use the host-managed credential broker.

POTCAR may be transferred only from a controlled user project according to the
approved run plan. Reports retain relative path, restricted classification,
size, hash, and dataset metadata only; POTCAR content never enters state or MCP
responses.
