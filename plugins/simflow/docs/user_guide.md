# SimFlow User Guide

## Installation

SimFlow is a Codex-native plugin. Install by placing the `simflow/` directory in your Codex plugins path.

## Quick Start

### 1. Build a Crystal Structure

```bash
# Build Si diamond structure
simflow-modeling build_structure --type diamond --element Si --lattice-const 5.43

# Build from parameters
simflow-modeling build_structure --type fcc --element Cu --lattice-const 3.61

# Build supercell
simflow-modeling make_supercell --input Si.cif --dims 2 2 2
```

### 2. Run a DFT Workflow

```bash
# Initialize workflow
simflow-dft init --structure Si.cif --workflow dft

# Dry-run to validate
simflow-dft dry_run

# Generate inputs
simflow-dft generate_inputs --code vasp --functional PBE

# Submit to HPC
simflow hpc submit --script-path job.sh --scheduler slurm

# Check status
simflow hpc status --job-id 12345

# Analyze results
simflow-dft analyze --stage relax
```

### 3. Run an AIMD Workflow

```bash
simflow-aimd init --structure Si.cif
simflow-aimd generate_inputs --code vasp --temp 300 --timestep 1
simflow hpc submit --script-path job.sh
simflow-aimd analyze --trajectory XDATCAR
```

### 4. Search Literature

```bash
simflow-mcp literature search --query "perovskite solar cell" --backend arxiv
simflow-mcp literature get_metadata --doi "10.1038/s41586-020-2649-2"
```

### 5. Search Structures

```bash
simflow-mcp structure search --formula "SiO2" --backend cod
simflow-mcp structure get --material_id "mp-149" --backend materials_project
```

## Workflow States

| State | Description |
|-------|-------------|
| `initialized` | Workflow created, no stages started |
| `running` | At least one stage in progress |
| `completed` | All stages completed successfully |
| `failed` | A stage failed and cannot recover |
| `paused` | User paused the workflow |

## Configuration

Create `.simflow/config.json` for local overrides:

```json
{
  "default_code": "vasp",
  "default_functional": "PBE",
  "hpc_scheduler": "slurm",
  "auto_checkpoint": true,
  "checkpoint_frequency": 3
}
```

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `MP_API_KEY` | Materials Project API key |
| `S2_API_KEY` | Semantic Scholar API key |
| `SIMFLOW_SSH_HOST` | SSH HPC host |
| `SIMFLOW_SSH_USER` | SSH username |
| `SIMFLOW_SSH_KEY` | SSH key file path |
