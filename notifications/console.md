# Console Notification Format

## Trigger
Any SimFlow event defined in `notification-policy.json`.

## Format
Console notifications are displayed directly in the Codex/OMX conversation.

## Template

```
[{level}] SimFlow: {event_type}
{message}
{details}
```

## Level Indicators
- `[INFO]` — Informational (stage complete, workflow complete)
- `[WARNING]` — Needs attention (approval required)
- `[ERROR]` — Failure (stage failed)
- `[DEBUG]` — Diagnostic (checkpoint created)

## Examples

### Stage Complete
```
[INFO] SimFlow: Stage 'modeling' completed
Artifacts: model.json (v1.0.0), POSCAR (v1.0.0)
Checkpoint: ckpt_003_modeling
Next: input_generation
```

### Stage Failed
```
[ERROR] SimFlow: Stage 'compute' failed
Error: SCF convergence not achieved after 200 iterations
Checkpoint: ckpt_005_compute (auto-created)
Recovery: Check INCAR parameters, increase NELM
```

### Approval Required
```
[WARNING] SimFlow: Approval required
Gate: hpc_submit
Action: Submit VASP job to SLURM (16 nodes, 4 hours)
Confirm to proceed or deny to abort.
```
