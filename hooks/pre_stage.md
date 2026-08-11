# Pre-Task Advisory Hook

## Trigger

Before a bounded research task when input ambiguity could affect quality or
safety.

## Checks

1. Identify the immediate user intent.
2. Select at most one Task Skill and one optional Domain Skill.
3. Inspect existing files, conventions, and scientific assumptions.
4. Report missing inputs or uncertainty that blocks useful work.
5. Escalate to runtime only for durable state, approval, execution, or recovery.

This hook is advisory. It does not require a prior stage, state read, phase
directory, or workflow transition.
