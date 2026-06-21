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

Submit script handling is preserve-first. If the user provides `job_script` or
`submit_script`, the computation stage records and hashes that script without
editing it. If no script is provided, SimFlow may reuse a single
scheduler-compatible script from the project reusable library
`scripts/submit/`. Multiple candidates require an explicit user choice. Only
when no suitable script exists should SimFlow generate a new script under
`.simflow/artifacts/compute/`.

Reusable submit scripts belong under `scripts/submit/`. One-off calculation
scripts should remain in their calculation directory or be referenced
explicitly. If a reusable script uses declared `{{SIMFLOW_*}}` placeholders and
the user requests rendering, SimFlow writes a derived copy under `.simflow/`
and records lineage to the original; it must not modify the original script in
place.

The standard computation helper emits the following evidence package:

| Evidence | Canonical path |
| --- | --- |
| Calculation manifest | `.simflow/artifacts/compute/calculation_manifest.json` |
| Input validation | `.simflow/artifacts/compute/input_validation.json` |
| Resource estimate | `.simflow/artifacts/compute/resource_estimate.json` |
| Credential scan | `.simflow/artifacts/security/credential_scan.json` |
| Dry-run report | `.simflow/artifacts/compute/dry_run_report.json` |

`dry_run_report.json` must report `status` as `pass`, `warning`, or `fail`.
It also carries the job `script_hash`, `input_artifact_hash`, and
`input_manifest_hash` that submit connectors compare against the current script
and approved evidence.

## Approval Gate

Real submission requires an approval gate decision tied to evidence. The target
submit contract requires:

- `approval_token` or `gate_decision_id`
- dry-run evidence path
- script hash approved by the gate
- input artifact hash or manifest hash approved by the gate
- scheduler or execution backend
- project root

The compute plan exposes these fields through `submit_readiness`. It is a
handoff payload for submit tools, not approval by itself. A real submit remains
blocked until the evidence-based `hpc_submit` gate has an approved decision for
the same project and hashes.

Submission must be blocked when:

- the project root does not contain initialized SimFlow workflow state
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

After a successful real `hpc.submit`, the MCP submit tool writes a
`job_record_if_submitted` computation artifact and appends the same record to
`.simflow/state/jobs.json`. This record is the evidence that makes the
conditional computation readiness key `job_record_if_submitted` present.
