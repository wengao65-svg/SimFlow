# State and Checkpoint Management

## .simflow Directory Structure

```
.simflow/
├── state/
│   ├── workflow.json      # Overall workflow state
│   ├── stages/
│   │   ├── relax.json     # Per-stage state
│   │   ├── scf.json
│   │   └── bands.json
│   ├── jobs/
│   │   └── job_001.json   # HPC job tracking
│   └── artifacts.json     # Artifact registry
├── artifacts/
│   ├── initial_structure.cif
│   ├── relaxed_structure.cif
│   └── energy.dat
├── checkpoints/
│   ├── relax_001.tar.gz
│   └── scf_001.tar.gz
├── extensions/
│   └── skills/            # Custom skill overrides
├── logs/
│   └── workflow.log
└── config.json            # Local overrides
```

## State Lifecycle

1. **Initialize**: `init_workflow` creates workflow.json and stage stubs
2. **Running**: Stage transitions update stage status
3. **Completed**: Artifacts registered, checkpoint created
4. **Recovery**: Load last checkpoint, resume from that stage

## Recovery Strategy

1. Find the last completed stage checkpoint
2. Extract artifacts from checkpoint
3. Update state to reflect recovered artifacts
4. Resume workflow from the next stage

## State Schema

Workflow state follows `schemas/state.schema.json`:

```json
{
  "workflow_id": "dft_scf_001",
  "workflow_type": "dft",
  "status": "running",
  "current_stage": "relax",
  "stages": {
    "input_gen": {"status": "completed"},
    "relax": {"status": "running"}
  },
  "artifacts": {
    "initial_structure": {"path": "...", "stage": "input_gen"}
  },
  "created_at": "2026-05-01T10:00:00Z",
  "updated_at": "2026-05-01T10:05:00Z"
}
```
