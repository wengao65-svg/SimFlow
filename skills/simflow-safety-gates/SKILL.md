---
name: simflow-safety-gates
description: Use when an action may submit jobs, access remote systems, handle credentials, touch licensed files, or perform destructive operations.
---

# SimFlow Safety Gates

## Trigger conditions

- A local, remote, or HPC job may be submitted.
- Credentials, private data, licensed/proprietary files, destructive file operations, or external systems are involved.
- A stage boundary requires evidence review before continuing.

## Input conditions

- Gate id or approval trigger, project root, relevant artifacts, dry-run evidence, validation reports, credential scan report, hashes, and requested action.
- Optional user approval text, approval token, gate decision id, job script, manifest, or resource estimate.
- The gate must evaluate recorded evidence; agent-supplied booleans are not sufficient.

## Output artifacts

- Gate evaluation report with condition results and referenced evidence.
- Gate decision record with stable id, decision, approver context, timestamp, and artifact hashes.
- Failure or warning report when evidence is missing, stale, inconsistent, or insufficient.

## Status write rules

- Write gate decisions to `.simflow/state/gates.json` under explicit `project_root`.
- Link gate decisions to dry-run, validation, credential scan, manifest, script hash, and artifact hash records.
- Preserve denial, warning, and stale-approval evidence for later review.

## Checkpoint rules

- Create a checkpoint before high-risk action approval and after the decision is recorded.
- Create a failure checkpoint when a gate blocks or evidence is incomplete.

## Prohibited actions

- Do not approve or execute high-risk actions from boolean-only context.
- Do not submit jobs, access remote systems, handle credentials, or touch licensed/proprietary files without matching evidence and explicit approval.
- Do not save credentials in state, logs, reports, artifacts, or checkpoints.
- Do not reuse approval when the script, inputs, manifest, or hash changed.

## Manual confirmation scenarios

- Approval text is ambiguous, stale, or does not match the requested action.
- Credential scan, dry-run, validation, or artifact hash evidence is missing.
- The operation is remote, costly, destructive, licensed, proprietary, or outside the workspace.
