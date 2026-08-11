# Console Notification Format

```text
[{level}] SimFlow: {event_type}
{message}
{details}
```

Use `INFO` for a meaningful record or verified transfer, `WARNING` for missing
approval or partial evidence, `ERROR` for failed operations, and `DEBUG` for
diagnostic details. Do not print credentials, POTCAR content, or private paths.

Examples:

```text
[INFO] SimFlow: run plan prepared
Hash: {run_plan_hash}
Approval required: true
```

```text
[ERROR] SimFlow: calculation failed
Status: failed
Recovery checkpoint: none
Next: inspect SCF diagnostics before changing parameters
```
