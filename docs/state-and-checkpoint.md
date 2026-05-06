# State and Checkpoint Management

## .simflow Directory Structure

```
.simflow/
├── state/
│   ├── workflow.json      # Overall workflow state
│   ├── stages.json        # Stage status registry
│   ├── artifacts.json     # Artifact registry
│   ├── checkpoints.json   # Checkpoint registry
│   ├── jobs.json          # HPC job tracking
│   ├── verification.json  # Gate verification state
│   └── summary.json       # Project status summary
├── artifacts/
│   ├── initial_structure.cif
│   ├── relaxed_structure.cif
│   └── energy.dat
├── checkpoints/
│   ├── relax_001.tar.gz
│   └── scf_001.tar.gz
├── reports/
│   └── status_summary.md
├── extensions/
│   └── skills/            # Custom skill overrides
├── logs/
│   └── workflow.log
└── config.json            # Local overrides
```

## State Lifecycle

1. **Initialize**: `simflow_state.init_workflow` creates the `.simflow/` tree, required state registries, and status summary files
2. **Running**: Stage transitions update stage status
3. **Completed**: Artifacts registered, checkpoint created
4. **Recovery**: Load last checkpoint, resume from that stage

## Host State Boundary

`.omx/` is owned by oh-my-codex / the host session. SimFlow may read `.omx/` for host context, but `.omx/` is never the SimFlow workflow state root. Initializing SimFlow in a project that already contains `.omx/` must leave `.omx/` untouched and create or update only `.simflow/` for workflow state.

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
