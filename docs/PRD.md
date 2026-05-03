# SimFlow Product Requirements Document

## Product Overview

SimFlow is a Codex-native computational simulation workflow layer for condensed matter physics and materials science. It provides structured, reproducible workflows for DFT, AIMD, and MD simulations.

## Target Users

- Computational materials scientists running DFT/AIMD/MD workflows
- Researchers who need reproducible simulation pipelines
- Teams managing HPC job submissions across multiple clusters

## Core Capabilities

1. **Workflow Management**: Define multi-stage simulation workflows (DFT, AIMD, MD) with gates and policies
2. **Skill System**: Modular, reusable simulation steps (structure building, input generation, analysis)
3. **MCP Integration**: External service connectors for literature search, structure databases, HPC management
4. **State Tracking**: Persistent workflow state with checkpoints and artifact lineage
5. **Verification Gates**: Automated quality checks at each workflow stage

## Feature Matrix

| Feature | Status |
|---------|--------|
| DFT workflow (SCF → Bands → DOS → Relax) | Implemented |
| AIMD workflow (Build → Input → Run → Analyze) | Implemented |
| MD workflow (Build → ForceField → Equilibrate → Production) | Implemented |
| Structure building (pymatgen/ASE) | Implemented |
| Input generation (VASP/QE/LAMMPS) | Implemented |
| Trajectory analysis (MDAnalysis) | Implemented |
| Literature search (arXiv, Crossref, Semantic Scholar) | Implemented |
| Structure database (Materials Project, COD) | Implemented |
| HPC submission (SLURM, PBS, SSH, Local) | Implemented |
| Custom skill extensions | Implemented |
| Checkpoint and recovery | Implemented |

## Success Criteria

- Users can run a complete DFT workflow from structure to results in under 10 commands
- All workflow artifacts are tracked with full lineage
- Jobs can be submitted to any supported HPC scheduler
- Missing credentials gracefully fall back to mock/dry-run mode
