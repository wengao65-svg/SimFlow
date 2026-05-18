# HPC Integration Guide

## Positioning

HPC integration is a safety-gated helper inside the `computation` stage. It is
not a standalone SimFlow CLI workflow and it must not bypass the SimFlow
approval model.

All real execution targets are treated as risky:

- SLURM
- PBS/Torque
- SSH remote execution
- local shell execution

Local execution is included because it can still consume resources, mutate
files, or run destructive commands.

## Dry-Run First

Compute actions start with dry-run evidence. A dry-run package should record:

- calculation manifest
- input file list and hashes
- job script path and hash
- resource estimate
- environment or command description
- input validation report
- credential scan result
- warnings and unresolved risks

The dry-run report is an artifact. Later approval must reference that artifact
instead of relying on an agent-supplied boolean.

## Approval Gate

Real submission requires an approval gate decision tied to evidence. The target
submit contract requires:

- `approval_token` or `gate_decision_id`
- dry-run artifact id
- script hash approved by the gate
- input artifact hash or manifest hash approved by the gate
- scheduler or execution backend
- project root

Submission must be blocked when:

- approval is missing
- dry-run evidence is missing
- input validation evidence is missing
- credential scan evidence is missing or unresolved
- the current job script hash differs from the approved dry-run artifact
- the current input manifest hash differs from the approved dry-run artifact

## Connector Responsibilities

Connectors may generate scripts, validate scripts, submit jobs, query status,
and cancel jobs. They must not decide whether submission is safe. That decision
belongs to the gate engine and the recorded approval decision.

All connectors should share the same approval semantics:

- SLURM: `sbatch`
- PBS/Torque: `qsub`
- SSH: remote scheduler or `nohup bash`
- Local: `bash` or equivalent local process execution

## Credential Security

- SSH and service credentials are read from environment variables or host secret
  mechanisms only.
- Credentials must not be copied into job scripts, artifacts, logs,
  checkpoints, or reports.
- Credential scans should be recorded before approval.
- Proprietary or licensed files must be identified and handled only with
  user-approved boundaries.

## Handoff

After a compute preparation or submission step, handoff notes should state:

- what was prepared or submitted
- where it is expected to run
- which inputs and scripts were used
- which hashes were approved
- whether outputs are complete, partial, missing, or unknown
- what checkpoint records the current state
