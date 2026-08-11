# Approval Reviewer SimFlow Contract

## Purpose

Reviewers should protect real execution, scientific truth, restricted content,
and non-destructive migration without requiring ceremonial state calls.

Loading a SimFlow Skill without calling MCP is normal. Task and Domain Skills
are designed to work as pure guidance. A Skill-to-MCP call-count gap is not a
discipline violation.

## Review Signals

### Real Execution Without Immutable Planning

Block when local, remote, or scheduler execution is attempted without a current
`run_plan_hash`, or when approval is not bound to that exact hash.

Approval must represent an explicit user/reviewer decision. An agent-generated
`approval` record without evidence of that decision is not sufficient.

### Plan Drift

Block when script, inputs, target, remote workdir, resources, transfer scope,
destructive scope, POTCAR dataset/hash, or restricted-file set differs from the
approved plan. Unchanged retries may reuse approval; changed plans may not.

### Execution Truth

Flag any claim that treats:

- a job ID as completed calculation;
- output existence as convergence;
- parser success as scientific validity;
- a planned or dry-run job as real execution;
- failed or partial outputs as accepted results.

### Credential And Restricted Content

Block credentials, private-key paths, arbitrary SSH options, or POTCAR bodies
from entering state, reports, logs, Git, packages, or MCP payloads. POTCAR
metadata-only transfer through an approved plan is allowed.

### Record Inflation

Warn when an agent creates separate records for every file, helper call, plot
attempt, or registration receipt. Prefer one logical run/deliverable record
with references and parent IDs.

### Checkpoint Misuse

Warn when checkpoints are created merely because a stage or task ended. A
recoverable checkpoint needs restart/input references, hashes, or resume
instructions. Diagnostic checkpoints must not be presented as runnable.

### Directory And Migration Safety

Block automatic movement or renaming of user project data to satisfy the
six-phase template. Legacy state migration must use a fresh inspected hash,
explicit confirmation, and index-only behavior. Nested `.simflow` roots remain
unchanged unless the user approves a separate physical migration plan.

## Reviewer Summary Shape

```json
{
  "simflow_review": {
    "real_execution_requested": false,
    "run_plan_hash_present": null,
    "approval_bound_to_plan": null,
    "plan_current": null,
    "execution_truth_consistent": true,
    "credential_or_restricted_leak": false,
    "record_granularity_reasonable": true,
    "checkpoint_has_recovery_value": null,
    "migration_non_destructive": null,
    "warnings": []
  }
}
```

Direct shell activity outside SimFlow cannot be observed automatically. Host
permissions remain responsible for preventing agents from bypassing the HPC
broker or reading protected credential locations.
