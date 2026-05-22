---
name: simflow-computation
description: Use when a user asks to prepare, validate, dry-run, or submit computational simulation jobs.
---

# SimFlow Computation

## Trigger conditions

- The user asks to prepare inputs, validate a calculation setup, estimate resources, dry-run a job, or submit a local, remote, or HPC job.
- The current research intent is computation, including input preparation as an optional sub-activity.
- A planned job needs evidence, approval, or handoff before execution.

## Input conditions

- User-provided or generated input files, model artifacts, calculation manifest, previous checkpoint, or explicit calculation plan.
- Optional software, scheduler, resource, environment, license, or cluster information.
- Approval evidence is required before real local, remote, or HPC execution.

## Output artifacts

- Calculation manifest describing software, commands, inputs, resources, environment, and intended outputs.
- Input validation report, dry-run report, resource estimate, credential scan report, and script or input hashes.
- Job record only when a real job is approved and submitted; waiting or planned jobs must remain labeled as such.

## Status write rules

- Resolve `project_root` explicitly before writing `.simflow/` state, artifacts, gates, or checkpoints.
- Register scripts, inputs, validation results, dry-run evidence, hashes, and job records as artifacts with lineage.
- Record approval gate decisions by id; do not replace evidence with agent-provided boolean flags.

## Checkpoint rules

- Create a checkpoint before any real submission decision and after dry-run or validation completes.
- Create a failure checkpoint if validation, credential scanning, approval, or submission fails.

## Prohibited actions

- Do not submit real local, remote, or HPC jobs without passing the relevant approval gate.
- Do not skip dry-run, input validation, resource estimate, credential scan, or artifact hash recording when real execution is possible.
- Do not store credentials, expose licensed or proprietary files, or report unfinished jobs as completed.
- Do not require one specific simulation engine, scheduler, parser, plotting library, or input builder.

## Manual confirmation scenarios

- Real execution, remote access, licensed software, proprietary files, or destructive file operations are involved.
- Resource requests, wall time, queue, account, environment, or software version are uncertain.
- The job script or input hash differs from the evidence used for approval.
