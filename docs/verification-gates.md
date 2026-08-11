# Verification And Approval Boundaries

## Scope

Verification has two owners:

- Research Task and Domain Skills own scientific checks such as model
  validity, convergence, units, statistics, and claim-evidence consistency.
- Runtime owns execution truth, path/hash validation, credentials, restricted
  material handling, approval, and recovery references.

There is no public `simflow-verify` or `simflow-safety-gates` Skill. Runtime
policies are internal constraints, not extra instructions that every task must
load.

## Immutable Run-Plan Approval

Real local, remote, or scheduler execution uses the following boundary:

1. `hpc/plan` validates the script and inputs, scans credentials, identifies
   restricted files, and persists an immutable plan.
2. The user reviews the target, resources, scope, warnings, and
   `run_plan_hash`.
3. An approval record is created for that exact hash.
4. `hpc/transfer` or `hpc/submit` recomputes the plan identity before acting.

Approval is blocked or invalidated when:

- no explicit approval reference is supplied;
- the recorded decision is not approved;
- the approval belongs to a different hash;
- script or input content changed;
- target, remote directory, resources, transfer scope, destructive scope, or
  restricted-file metadata changed;
- credential scanning fails;
- an SSH operation lacks a valid broker or required transfer manifest.

An unchanged retry may reuse approval. A changed plan must be reviewed again.
Boolean claims such as `approved=true` or `dry_run=true` do not replace the
persisted plan and approval record.

## Other Policy Gates

Workflow gate definitions may evaluate recorded evidence for bounded policy
decisions such as production-readiness review. They may record approval or
rejection, but they must not silently submit work or claim scientific success.

Scientific readiness and submit readiness are separate. A model may be judged
ready for a proposed production run while the actual execution remains blocked
until its immutable plan is approved.

## Actions On Failure

When a boundary fails:

- stop the risky action;
- report the failed condition and current plan hash;
- do not record execution as completed;
- preserve failure logs or one compact failure record when durable history is
  useful;
- create a checkpoint only if real restart references or a meaningful
  diagnostic recovery boundary exist.

Ordinary failure, task completion, or stage boundaries do not automatically
create checkpoints.

## Policy Constraints

Runtime policies may enforce:

- explicit project-root and path confinement;
- dry-run planning before real execution;
- approval bound to immutable execution identity;
- credential and restricted-content exclusion;
- manifest and hash verification;
- truthful run status and compact recovery.

They must not enforce a fixed phase layout, select the scientific method,
require per-file artifact registration, or turn parser success into scientific
acceptance.
