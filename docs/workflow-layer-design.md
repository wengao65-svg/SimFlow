# Workflow Layer Design

## Stage Model

A workflow is a directed acyclic graph of stages. Each stage represents a discrete computation step.

### Stage Definition

```json
{
  "name": "relax",
  "description": "Structural relaxation",
  "default_skill": "simflow-dft:run_relax",
  "required_inputs": ["structure"],
  "expected_outputs": ["relaxed_structure", "energy"],
  "validators": ["convergence_check"]
}
```

### Stage Dependencies

Stages declare dependencies via `stage_dependencies`:

```json
{
  "stage_dependencies": {
    "bands": ["relax"],
    "dos": ["relax"],
    "relax": ["input_gen"]
  }
}
```

## State Model

Each stage has a state tracked in `.simflow/state/stages/`:

```json
{
  "stage": "relax",
  "status": "completed",
  "started_at": "2026-05-01T10:00:00Z",
  "completed_at": "2026-05-01T12:30:00Z",
  "artifacts": ["relaxed_structure", "energy"],
  "checkpoint": ".simflow/checkpoints/relax_001.tar.gz"
}
```

## Artifact Model

Artifacts are simulation outputs tracked with full lineage:

```json
{
  "name": "relaxed_structure",
  "type": "structure",
  "stage": "relax",
  "path": ".simflow/artifacts/relaxed_structure.cif",
  "created_at": "2026-05-01T12:30:00Z",
  "lineage": {
    "inputs": ["initial_structure"],
    "parameters": {"encut": 520, "ediff": 1e-6}
  }
}
```

## Checkpoint Strategy

- Each stage creates a checkpoint on completion
- Checkpoints contain all stage outputs and state
- Recovery resumes from the last successful checkpoint
- Checkpoint files are compressed tar archives

## Workflow Templates

Three built-in workflow templates:

1. **DFT Workflow**: input_gen → relax → scf → bands → dos → analysis
2. **AIMD Workflow**: build_structure → generate_inputs → run_md → analyze_trajectory
3. **MD Workflow**: build_structure → setup_forcefield → equilibrate → production_run → analyze
