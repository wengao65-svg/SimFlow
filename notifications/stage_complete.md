# Task Completion Notification

Use only when a user-facing completion message is useful.

```text
[SimFlow] Task completed: {summary}
Evidence: {key_references}
Record: {record_id_or_none}
Recovery checkpoint: {checkpoint_id_or_none}
Next: {next_action}
```

The record and checkpoint fields may be absent. Completion does not create them
automatically.
