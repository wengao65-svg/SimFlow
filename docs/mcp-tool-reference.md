# MCP Tool Reference

SimFlow MCP tools use `<server>/<tool>` names. State-changing tools require an
explicit `project_root`; most also require `simflow_state/read_state` in the
same session before the write is accepted.

## State And Recovery

| Tool | Purpose | Important behavior |
|---|---|---|
| `simflow_state/read_state` | Read a canonical state file | Starts the 30-minute MCP engagement session |
| `simflow_state/init_workflow` | Initialize `.simflow/` | Idempotent by default; `force=true` first backs up the existing tree |
| `simflow_state/update_stage` | Change a stage status | Completion creates a pending verification record |
| `simflow_state/workflow_status` | Read project status | Read-only; first call auto-satisfies the engagement prerequisite |
| `simflow_state/orphan_compute_scanner` | Find unregistered calculation directories | Reports risky names such as `NoGate`, `Bypass`, and `SkipGate` |
| `simflow_state/record_user_override` | Record an explicitly approved bypass | Requires approver context and a risk note |
| `simflow_state/record_stage_failure` | Persist a stage failure | Writes sanitized log/report artifacts, failed state, fail verification, and a diagnostic checkpoint |
| `simflow_state/repair_state` | Audit or repair inconsistent state | `audit` is read-only; `apply` requires engagement, confidence above 0.8, and creates a full backup |
| `simflow_state/session_handoff` | Generate a re-entry summary | Writes `.simflow/reports/session_handoff_<timestamp>.md` |

## Artifacts

| Tool | Purpose | Important behavior |
|---|---|---|
| `artifact_store/register` | Register a file, directory, or planned artifact | Atomically synchronizes artifact, lineage, and stage output state |
| `artifact_store/list` | List registered artifacts | Read-only |
| `artifact_store/get` | Read one artifact record | Read-only |

Directory artifacts use `sha256-path-size-content-v1`: relative paths, sizes,
and file content hashes all contribute to the tree hash. Registration records
the current `workflow_id` and appends the artifact ID to the producing stage's
`outputs` without duplication.

## HPC Transfers

`hpc/upload` and `hpc/download` are the supported remote transfer path. They
require an explicit `project_root`, `scheduler: "ssh"`, an approved
`hpc_transfer` decision, and non-empty relative `paths`. Local paths must stay
inside `project_root`; remote directories must be absolute POSIX paths without
`..` components.

Both tools expand requested directories, write a transfer manifest, and verify
`sha256-path-size-content-v1` before returning `verified`. Partial transfers and
hash mismatches return an error while preserving a `transfer_manifest`
computation artifact. Credentials remain environment-only.

An SSH submit must reference the verified upload manifest through
`transfer_manifest` and use the matching `remote_workdir`; it no longer copies
only the script to `/tmp`.

## Checkpoints

| Tool | Purpose | Important behavior |
|---|---|---|
| `checkpoint_store/create` | Create a state snapshot | Success/partial snapshots require workflow and stage state |
| `checkpoint_store/list` | List checkpoints | Read-only |
| `checkpoint_store/restore` | Restore a checkpoint | Diagnostic-only checkpoints are rejected |

Failure checkpoints capture the failed state and error evidence. They are not
the default recovery target. Recovery should use the most recent successful,
recoverable checkpoint reported by `record_stage_failure` or session handoff.

## Engagement Contract

Protected writes return `skill_engagement_contract_violation` until
`simflow_state/read_state` has been called. A first read-only status/readiness
call may bootstrap that read automatically. Protected writes never auto-grant
their own prerequisite. The session timeout defaults to 30 minutes and is
configured by `SIMFLOW_SESSION_TIMEOUT_MIN`.

`repair_state` defaults to `audit`. Apply mode only repairs structural metadata
with confidence at or above the requested threshold: workflow identity fields,
lineage projections, stage declarations/outputs, known checkpoint status and
recoverability, canonical live-path casing, and summary projection. It does not
rewrite checkpoint snapshots, recompute scientific checksums, infer scientific
completion, or fabricate missing lineage parents.
