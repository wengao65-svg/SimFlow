# SimFlow

A **Codex-native** computational simulation workflow layer for agentic research.

SimFlow is not a centralized workflow executor. It does not decide the science
for Codex, Claude Code, or another host agent. The host agent chooses the
literature sources, modeling tools, simulation engines, analysis code, and
writing format. SimFlow records the process so computational research remains
traceable, recoverable, reviewable, and safety-gated.

## Architecture

```
Codex / OMX Host
  -> SimFlow Skills          (intent-specific workflow guidance)
  -> SimFlow Workflow Layer  (research stages, recipes, gates, policies)
  -> MCP Servers             (state, artifacts, lineage, checkpoints, gates)
  -> Runtime Helpers         (optional parsers, validators, templates)
  -> .simflow/               (per-project state, artifacts, checkpoints)
```

## Features

- **Research Stage Semantics**: literature review, proposal, modeling, computation, analysis/visualization, and writing
- **Recipes, Not Fixed DAGs**: DFT, AIMD, classical MD, phonon, NEB, defect, adsorption, and custom paths are reference recipes or tags
- **Artifact Lineage**: inputs, scripts, outputs, figures, and claims can be traced through registered artifacts
- **Checkpoint Recovery**: stage boundaries create recoverable state checkpoints
- **Safety Gates**: real local, remote, or HPC execution is dry-run first and requires approval
- **Domain Helpers**: optional VASP, CP2K, QE, LAMMPS, Gaussian, parser, plotting, and structure helpers
- **MCP Recording Tools**: project state, artifact, checkpoint, lineage, gate, and handoff records
- **Custom Skills**: project-specific skill extensions under `.simflow/extensions/skills/`

## Workflow Layer Contract

| Concept | Meaning |
|---------|---------|
| Stage | Research intent and evidence boundary |
| Recipe | Optional reference path such as DFT, AIMD, classical MD, phonon, or NEB |
| Artifact | Registered output with metadata, checksum, and lineage |
| Checkpoint | Recoverable snapshot at a stage boundary |
| Gate | Evidence-based approval or verification boundary |

Default top-level stages are `literature_review`, `proposal`, `modeling`,
`computation`, `analysis_visualization`, and `writing`. A project may enter any
stage directly when the needed inputs and evidence are present.

## Domain Helpers

| Helper | Typical use |
|--------|-------------|
| VASP | DFT, AIMD, phonon, NEB, defects, surfaces, output inspection |
| CP2K | Quickstep DFT, AIMD, common CP2K task checks |
| Quantum ESPRESSO | Plane-wave DFT input and output guidance |
| LAMMPS | Classical MD setup and trajectory analysis guidance |
| Gaussian | Quantum chemistry input and output guidance |

These helpers suggest and validate. They do not limit what the host agent can
do, and they should return uncertainty rather than silently mapping unknown
tasks to a default calculation.

## Quick Start

### Codex

Install the published SimFlow Codex marketplace:

```bash
codex plugin marketplace add wengao65-svg/SimFlow --ref codex-marketplace
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

Update the marketplace when a new SimFlow version is published:

```bash
codex plugin marketplace upgrade simflow-marketplace
codex
```

After upgrading, restart Codex or open a new thread. If needed, use `/plugins` to update or reinstall `simflow`.

Developer local debugging uses the source checkout and local wrapper installer:

```bash
git clone https://github.com/wengao65-svg/SimFlow.git ~/simflow
cd ~/simflow
npm install
npm run install:codex
codex
```

SimFlow skills are invoked through Codex skill routing, for example `$simflow`, `$simflow-vasp`, `@simflow-vasp`, or a natural-language request. `/simflow` is not a SimFlow invocation path.

`npm run install:codex` is for developer local debugging. It generates a wrapper marketplace at `~/.cache/simflow/codex-marketplace` and registers that wrapper with Codex. The published `codex-marketplace` branch has the same Codex marketplace shape:

```text
.agents/plugins/marketplace.json
plugins/simflow/
```

The marketplace entry uses `source.path: "./plugins/simflow"`. The source repository root is not the default marketplace root because current Codex CLI builds reject root-local plugin entries such as `source.path: "./"`.

Maintainers build and publish the Codex marketplace branch from `main`:

```bash
npm run build:codex-marketplace
npm run publish:codex-marketplace
```

`npm run build:marketplace` remains available as a local wrapper build command. `plugins/simflow` is copied as a real directory, not a symlink.

`/skills` can be used as an enhanced check when the active Codex build supports it, but SimFlow release acceptance is based on `/plugins`, `/mcp`, valid `SKILL.md` frontmatter, and real skill triggering through `$simflow`, `$simflow-vasp`, `@simflow-vasp`, or natural-language tasks.

### Claude Code

Install the published SimFlow Claude marketplace branch with Claude's source ref syntax:

```bash
claude plugin marketplace add wengao65-svg/SimFlow@claude-marketplace
claude plugin install simflow@simflow-claude-marketplace
```

For a git URL, use `#claude-marketplace`:

```bash
claude plugin marketplace add https://github.com/wengao65-svg/SimFlow.git#claude-marketplace
```

Developer local debugging uses the generated Claude marketplace wrapper:

```bash
npm run build:claude-marketplace
claude plugin marketplace add ./dist/claude-marketplace
claude plugin install simflow@simflow-claude-marketplace
```

Claude plugin skills are namespaced, for example `/simflow:simflow`, `/simflow:simflow-vasp`, `/simflow:simflow-cp2k`, and `/simflow:simflow-writing`. The Claude adapter is a parallel distribution layer; it does not replace the Codex marketplace, Codex install/update flow, MCP startup wrapper, or workflow business logic.

## Project Structure

```
simflow/
├── skills/                    # Workflow-layer and domain helper skills
├── workflow/                  # Stage, recipe, gate, policy definitions
│   ├── stages/                # Research intent contracts
│   ├── recipes/               # Optional JSON reference recipes
│   └── gates/                 # Verification and approval gates
├── mcp/                       # MCP servers and connectors
│   ├── servers/
│   │   ├── literature/        # arXiv, Crossref, Semantic Scholar
│   │   ├── structure/         # Materials Project, COD
│   │   ├── hpc/               # SLURM, PBS, SSH, Local
│   │   └── state/             # Workflow state management
│   └── shared/                # Retry, cache, credentials, transport
├── runtime/                   # Core runtime and optional helpers
│   ├── simflow_core/          # State, artifact, checkpoint, gates, workflow facade
│   └── simflow_helpers/       # Optional helper implementations
├── templates/                 # Optional helper templates
├── schemas/                   # JSON schemas for validation
├── tests/                     # Unit, MCP, E2E tests
├── docs/                      # Design and user documentation
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
- [Claude Code Quick Start](docs/quickstart_claude.md)
- [Installation Guide](docs/installation.md)
- [User Guide](docs/user_guide.md)
- [Technical Design](docs/technical-design.md)
- [Workflow Design](docs/workflow-layer-design.md)
- [Skill Design](docs/skill-design.md)
- [MCP Design](docs/mcp-design.md)
- [HPC Integration](docs/hpc-integration.md)
- [Custom Skills](docs/custom-skills.md)
- [Credentials Policy](docs/credentials-policy.md)
- [Docs Index](docs/README.md)

## License

MIT
