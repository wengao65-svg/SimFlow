# Verification Gates

## Overview

Gates are automated quality checks that run between workflow stages. A stage cannot advance until all its gates pass.

## Gate Types

| Gate | Trigger | Action |
|------|---------|--------|
| `convergence_check` | After SCF/relax | Check electronic/ionic convergence |
| `energy_convergence` | After relax | Verify energy change < threshold |
| `force_convergence` | After relax | Verify max force < threshold |
| `structure_validity` | After structure build | Check lattice, bonds, overlaps |
| `trajectory_integrity` | After MD run | Verify trajectory frames exist |
| `input_validation` | Before submission | Validate input file syntax |
| `output_completeness` | After run | Check all expected outputs exist |
| `rdf_convergence` | After AIMD equilibration | Verify RDF has converged |
| `pressure_convergence` | After NPT equilibration | Verify pressure has converged |

## Gate Definition

```json
{
  "gate_name": "convergence_check",
  "description": "Verify SCF/relaxation convergence",
  "trigger_stage": "relax",
  "condition": "converged == true",
  "action_on_fail": "block_and_warn",
  "parameters": {
    "max_steps": 100,
    "energy_tolerance": 1e-6
  }
}
```

## Actions on Failure

- `block_and_warn`: Stop workflow, notify user
- `retry`: Re-run the stage with adjusted parameters
- `skip_with_warning`: Log warning, continue anyway
- `rollback`: Revert to previous checkpoint

## Policy Layer

Policies are workflow-wide constraints that complement gates:

| Policy | Description |
|--------|-------------|
| `max_walltime` | Total workflow walltime limit |
| `max_jobs` | Maximum concurrent HPC jobs |
| `resource_budget` | Compute hour budget |
| `data_retention` | Artifact retention period |
| `approval_required` | Stages requiring manual approval |
| `auto_checkpoint` | Automatic checkpoint frequency |

## Workflow Integration

Gates are declared in workflow definitions:

```json
{
  "workflow_name": "dft",
  "stages": ["input_gen", "relax", "scf"],
  "gates": {
    "relax": ["convergence_check", "energy_convergence"],
    "scf": ["convergence_check"]
  },
  "policies": ["max_walltime", "auto_checkpoint"]
}
```
