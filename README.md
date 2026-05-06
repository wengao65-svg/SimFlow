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

Build and register the local Codex marketplace wrapper:

```bash
git clone <repo> ~/simflow
cd ~/simflow
npm install
npm run install:codex
codex
```

Then install SimFlow inside Codex:

```text
/plugins
```

Select and install `simflow`, then verify tools and skills:

```text
/mcp
$simflow
```

SimFlow skills are invoked through Codex skill routing, for example `$simflow`, `$simflow-vasp`, `@simflow`, or a natural-language request. `/simflow` is not a SimFlow invocation path.

`npm run install:codex` generates a wrapper marketplace at `~/.cache/simflow/codex-marketplace` and registers that wrapper with Codex. The wrapper has the Codex marketplace shape:

```text
.agents/plugins/marketplace.json
plugins/simflow/
```

The marketplace entry uses `source.path: "./plugins/simflow"`. The source repository root is not the default marketplace root because current Codex CLI builds reject root-local plugin entries such as `source.path: "./"`.

Remote marketplace installation is supported when the remote repository is a wrapper marketplace with a real `plugins/simflow/` directory:

```bash
codex plugin marketplace add <org>/simflow --ref <version>
```

`npm run build:marketplace` remains available for maintainers who want a clean wrapper at publish time, for example to publish a separate marketplace repository or release artifact. `plugins/simflow` is copied as a real directory, not a symlink.

`/skills` can be used as an enhanced check when the active Codex build supports it, but SimFlow release acceptance is based on `/plugins`, `/mcp`, valid `SKILL.md` frontmatter, and real skill triggering through `$simflow`, `$simflow-vasp`, `@simflow`, or natural-language tasks.

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

- [Codex 快速上手](docs/quickstart_codex.md)
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
