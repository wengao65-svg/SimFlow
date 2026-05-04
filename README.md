# SimFlow

A **Codex-native** computational simulation workflow layer for DFT, AIMD, and MD research.

SimFlow provides structured, reproducible workflows for condensed matter physics and materials science, integrating with HPC schedulers, literature databases, and structure databases.

## Architecture

```
Codex / OMX Host
  -> SimFlow Skills          (23 skills: modeling, DFT, AIMD, MD)
  -> SimFlow Workflow Layer  (9 stages, 9 gates, 6 policies)
  -> MCP Servers             (literature, structure, HPC, state)
  -> Runtime                 (state, artifact, checkpoint utilities)
  -> .simflow/               (per-project state, artifacts, checkpoints)
```

## Features

- **Workflow Management**: Declarative stage definitions with 9 verification gates and 6 policies
- **Template Engine**: Jinja2-compatible rendering for VASP/QE/LAMMPS/Gaussian inputs (no Jinja2 dependency)
- **Structure Building**: pymatgen/ASE for crystal structures (FCC, BCC, diamond, rocksalt, zincblende)
- **Input Generation**: VASP, Quantum ESPRESSO, LAMMPS input files
- **Trajectory Analysis**: MDAnalysis for RDF, MSD, energy analysis
- **Literature Search**: arXiv, Crossref, Semantic Scholar connectors with retry + caching
- **Structure Databases**: Materials Project, Crystallography Open Database (COD)
- **HPC Integration**: SLURM, PBS, SSH, local execution with gate-based approval
- **State Tracking**: Checkpoints, artifact lineage, workflow recovery
- **Custom Skills**: User-defined skill extensions

## Supported Workflows

| Workflow | Stages |
|----------|--------|
| DFT | input_gen → relax → scf → bands → dos → analysis |
| AIMD | build_structure → generate_inputs → run_md → analyze_trajectory |
| MD | build_structure → setup_forcefield → equilibrate → production_run → analyze |

## Supported Software

| Software | Use Case |
|----------|----------|
| VASP | DFT, AIMD |
| CP2K | AIMD, DFT (Quickstep) |
| Quantum ESPRESSO | DFT |
| LAMMPS | Classical MD |
| Gaussian | Quantum chemistry |

## Quick Start

```bash
# Build a structure
simflow-modeling build_structure --type diamond --element Si --lattice-const 5.43

# Run DFT workflow
simflow-dft init --structure Si.cif
simflow-dft generate_inputs --code vasp --functional PBE
simflow hpc submit --script-path job.sh --scheduler slurm

# Search literature
simflow-mcp literature search --query "perovskite solar cell"

# Search structures
simflow-mcp structure search --formula "SiO2" --backend cod
```

## Project Structure

```
simflow/
├── skills/                    # 4 skill groups, 23 skills
│   ├── simflow-modeling/      # Structure building, validation
│   ├── simflow-dft/           # DFT workflow skills
│   ├── simflow-aimd/          # AIMD workflow skills
│   └── simflow-md/            # MD workflow skills
├── workflow/                  # Stage, gate, policy definitions
│   └── gates/                 # 9 verification gate definitions
├── agents/                    # 9 workflow agents
├── mcp/                       # MCP servers and connectors
│   ├── servers/
│   │   ├── literature/        # arXiv, Crossref, Semantic Scholar
│   │   ├── structure/         # Materials Project, COD
│   │   ├── hpc/               # SLURM, PBS, SSH, Local
│   │   └── state/             # Workflow state management
│   └── shared/                # Retry, cache, credentials, transport
├── runtime/                   # Libraries and scripts
│   ├── lib/                   # State, artifact, checkpoint, gates, template, parsers
│   └── scripts/               # CLI scripts for workflow operations
├── templates/                 # Input file templates (VASP, QE, LAMMPS, SLURM)
├── schemas/                   # 8 JSON schemas for validation
├── tests/                     # Unit, MCP, E2E tests (309 tests)
├── docs/                      # 16 documentation files
└── scripts/                   # Scaffold and utility scripts
```

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `MP_API_KEY` | Materials Project API key |
| `S2_API_KEY` | Semantic Scholar API key |
| `SIMFLOW_SSH_HOST` | SSH HPC host |
| `SIMFLOW_SSH_USER` | SSH username |
| `SIMFLOW_SSH_KEY` | SSH key file path |

Missing credentials gracefully fall back to mock/dry-run mode.

## Documentation

- [Installation Guide](docs/installation.md)
- [User Guide](docs/user_guide.md)
- [Technical Design](docs/technical-design.md)
- [Workflow Design](docs/workflow-layer-design.md)
- [Skill Design](docs/skill-design.md)
- [MCP Design](docs/mcp-design.md)
- [HPC Integration](docs/hpc-integration.md)
- [Custom Skills](docs/custom-skills.md)
- [Credentials Policy](docs/credentials-policy.md)

## Examples

- [DFT Workflow](docs/examples/dft_workflow.md)
- [AIMD Workflow](docs/examples/aimd_workflow.md)
- [MD Workflow](docs/examples/md_workflow.md)

## License

MIT
