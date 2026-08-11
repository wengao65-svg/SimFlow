# Pre-Submit Safety Hook

## Trigger

Before any real local, remote, or scheduler execution.

## Checks

1. Build or reload the immutable run plan.
2. Recompute script, input, target, resource, transfer, destructive, and
   restricted-file identity.
3. Confirm dry-run validation and credential scan did not fail.
4. Require explicit approval bound to the exact `run_plan_hash`.
5. For SSH, require the broker and a verified transfer manifest.

Any identity change invalidates approval. Submission remains blocked until the
current plan is approved.
