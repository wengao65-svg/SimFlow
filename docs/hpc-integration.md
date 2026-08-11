# HPC Integration Guide

## Positioning

HPC support is a narrow runtime boundary for real local, remote, and scheduler
execution. It is selected because the current task needs execution, not because
the project is in a particular stage or directory.

All real execution targets are approval-gated:

- local shell execution;
- SLURM;
- PBS/Torque;
- SSH-backed remote execution.

Local execution follows the same discipline because it can consume resources,
mutate files, or invoke destructive commands.

## Four-Tool Flow

The public HPC surface is:

```text
plan -> transfer -> submit -> status
```

`transfer` is optional for local work and for remote plans that do not move
files. There are no separate public upload or download tools.

### `plan`

`hpc/plan` receives an explicit `project_root`, job script, non-empty input
list, scheduler, resources, and any SSH or transfer declaration. It:

- preserves an existing user script or creates a bounded SLURM script only
  when explicitly requested;
- validates that paths stay inside the project;
- hashes the script and input manifest;
- scans planned content for credentials;
- identifies restricted files without persisting their bodies;
- binds target, remote directory, resources, transfer scope, and destructive
  scope into one immutable identity;
- writes the run-plan report under `.simflow/reports/hpc/plans/`.

The returned `run_plan_hash` is the unit of approval. Planning does not approve,
transfer, submit, or prove scientific correctness.

One-off job scripts should stay in their calculation directory. Reusable
scripts may stay in an existing project script library. SimFlow does not move
them into a fixed artifact directory.

### Approval

The host must obtain explicit user approval and persist an approval record
whose conditions contain the exact `run_plan_hash`. For example:

```json
{
  "kind": "approval",
  "summary": "Approve the reviewed run plan",
  "status": "approved",
  "details": {
    "gate": "hpc_submit",
    "conditions": {
      "run_plan_hash": "<exact hash from hpc/plan>"
    }
  }
}
```

`hpc/transfer` and `hpc/submit` require the resulting approval reference. The
runtime recomputes the plan identity before action. Changes to the script,
inputs, target, remote directory, resources, transfer scope, destructive scope,
or restricted-file metadata invalidate the approval. An unchanged retry or
resume may reuse it.

### `transfer`

`hpc/transfer` executes the `upload` or `download` direction already declared
inside the approved run plan. Callers cannot replace the plan's paths, target,
or directories at transfer time.

The runtime verifies source and destination manifests and writes one transfer
report plus one compact run record. A failed or partial transfer is recorded as
such; it is never promoted to a successful submit.

### `submit`

`hpc/submit` accepts the immutable hash and approval reference, then submits the
unchanged plan. SSH submit additionally requires the verified upload manifest.
Every attempt writes one compact run record.

A scheduler job ID proves only that submission occurred. It does not prove that
the calculation started, completed, converged, or produced scientifically valid
results.

### `status`

`hpc/status` queries bounded connector state for a job ID. Scheduler state and
scientific result validation remain separate facts. Output presence or parser
success must not be reported as convergence without domain-specific checks.

## Credential Broker

SSH targets contain only `host` plus optional `user` and `port`. Passwords,
private keys, key paths, and arbitrary SSH options are rejected.

Configure the broker for real SSH operations:

```bash
export SIMFLOW_HPC_BROKER_SOCKET="${XDG_RUNTIME_DIR:-/tmp}/simflow-hpc/broker.sock"
export SIMFLOW_HPC_BROKER_ALLOWED_ROOTS="/path/to/project-a:/path/to/project-b"
python3 scripts/start_hpc_broker.py
```

Start the broker in the environment that owns the required OpenSSH config or
SSH agent. The Agent-facing host receives only the broker socket variable and
must not inherit the broker's `SSH_AUTH_SOCK`. The owner-only socket checks peer
identity, accepts only bounded structured operations, and confines local paths
to configured project roots. Missing or unsafe broker configuration fails
closed.

Credentials must never be copied into scripts, records, reports, checkpoints,
logs, or packages.

## POTCAR And Restricted Files

A VASP POTCAR may be materialized only from a user-owned licensed library into
a controlled calculation directory with exact dataset selection. It may be
included in an approved transfer plan.

Run plans and transfer reports retain only metadata such as relative path,
restricted classification, size, SHA-256, element, dataset, and validation.
POTCAR content must never enter `.simflow`, Git, MCP responses, checkpoints, or
distribution packages.

## Recording And Recovery

Plan reports, transfer reports, and submit attempts are runtime facts. Do not
create per-file artifact registry entries or a separate jobs registry.

A checkpoint is optional and should be created only when real restart files,
input hashes, and a usable resume command form a recovery boundary. Ordinary
planning, submission, or stage completion does not require one.

A useful host handoff states the reviewed plan hash, target, latest scheduler
state, scientific validation status, risks, next action, and whether approval is
still valid. Handoff is a summary, not a mandatory runtime operation.
