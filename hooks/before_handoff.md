# Optional Handoff Hook

## Trigger

When the user requests a handoff or another agent needs durable context.

## Summary

- current goal;
- active or recent runs and their true status;
- meaningful deliverables;
- latest recoverable checkpoint, if one exists;
- unresolved risks and missing evidence;
- next action and approval needs.

A handoff is a host summary, not a mandatory runtime write. It must not create a
checkpoint or import host transcripts.
