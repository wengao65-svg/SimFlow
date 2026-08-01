# SimFlow

A computational simulation workflow layer for traceable, safety-gated agentic
research.

SimFlow is not a centralized workflow executor. It does not decide the science
for Codex, Claude Code, OpenCode, or another host agent. The host agent chooses the
literature sources, modeling tools, simulation engines, analysis code, and
writing format. SimFlow records the process so computational research remains
traceable, recoverable, reviewable, and safety-gated.

## Architecture

```
Host Agent (Claude Code, Codex, OpenCode, or compatible agent)
  -> SimFlow Skills          (intent-specific workflow guidance)
  -> SimFlow Workflow Layer  (research stages, recipes, gates, policies)
  -> MCP Servers             (state, artifacts, lineage, checkpoints, gates)
  -> Runtime Helpers         (optional parsers, validators, templates)
  -> .simflow/               (per-project state, artifacts, checkpoints)
```

## Features

- **Research Stage Semantics**: literature review, proposal, modeling, computation, analysis/visualization, and writing
- **Recipes, Not Fixed DAGs**: DFT, AIMD, classical MD, MLP-MD, phonon, NEB, defect, adsorption, and custom paths are reference recipes or tags
- **Artifact Lineage**: inputs, scripts, outputs, figures, and claims can be traced through registered artifacts
- **Checkpoint Recovery**: stage boundaries create recoverable state checkpoints
- **Safety Gates**: real local, remote, or HPC execution is dry-run first and requires approval
- **Domain Assistants**: VASP, CP2K, LAMMPS, GPUMD/NEP, and cross-tool MLP guidance with optional helper scripts
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

## Domain Assistants

| Domain Assistant | Typical use |
|------------------|-------------|
| VASP | DFT, AIMD, phonon, NEB, defects, surfaces, output inspection |
| CP2K | Quickstep DFT, AIMD, common CP2K task checks |
| LAMMPS | Classical MD setup and trajectory analysis guidance |
| GPUMD/NEP | Input generation, validation, dry-run planning, orchestration, selected output parsing, and MLP handoff |
| MLP | Cross-tool dataset, training, validation, active-learning, readiness, and handoff evidence guidance |
| QE / Gaussian | Unsupported placeholders; user-provided files can still be recorded as generic artifacts |

Domain Assistants guide software- or domain-specific work. They do not limit
what the host agent can do, and they should return uncertainty rather than
silently mapping unknown tasks to a default calculation.

The product role, helper support level, and helper output format are separate
concepts. A Domain Assistant may use optional helper scripts. The shared
toolchain contract records which tool capabilities are `helper_supported`,
while `simflow.helper_evidence.v1` is only the common helper-evidence output
format for scripts that produce such records.

GPUMD and NEP are helper-supported for bounded preparation, validation,
dry-run planning, selected parsing, and evidence handoff. The `simflow-gpumd`
Domain Assistant does not provide real execution, local submit, remote execution, or HPC
submit. `simflow-mlp` is a cross-tool MLP Domain Assistant, not a concrete MLP
engine executor.

Software and toolchain fields are planning/provenance metadata, not a mandatory
registration gate. Tools without built-in helpers can still be tracked through
artifacts and handoff records.

## Quick Start

Choose the distribution path for your host agent. Claude Code users install
from the published `claude-marketplace` branch, Codex users install from the
published `codex-marketplace` branch, and OpenCode users install the
`opencode-simflow` npm plugin.

### Claude Code

Install the published SimFlow Claude marketplace branch with Claude's source
ref syntax:

```bash
claude plugin marketplace add wengao65-svg/SimFlow@claude-marketplace
claude plugin install simflow@simflow-claude-marketplace
```

For a git URL, use `#claude-marketplace`:

```bash
claude plugin marketplace add https://github.com/wengao65-svg/SimFlow.git#claude-marketplace
claude plugin install simflow@simflow-claude-marketplace
```

Update SimFlow when a new Claude marketplace version is published:

```bash
claude plugin marketplace update simflow-claude-marketplace
claude plugin update simflow
```

After updating, restart Claude Code or open a new session so the updated plugin
is loaded.

Claude plugin skills are namespaced:

```text
/simflow:simflow
/simflow:simflow-vasp
/simflow:simflow-cp2k
/simflow:simflow-writing
```

See [Claude Code Quick Start](docs/quickstart_claude.md) for local testing,
validation, and Claude-specific details.

### Codex

Install the published SimFlow Codex marketplace:

```bash
codex plugin marketplace add wengao65-svg/SimFlow --ref codex-marketplace
codex
```

Then install `simflow` inside Codex with `/plugins`, and verify tools and
skills:

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

SimFlow skills are invoked through Codex skill routing, for example `$simflow`, `$simflow-vasp`, `@simflow-vasp`, or a natural-language request. `/simflow` is not a SimFlow invocation path.

See [Codex 快速上手](docs/quickstart_codex.md) for local wrapper debugging,
validation, and Codex-specific marketplace details.

### OpenCode

Install SimFlow globally for OpenCode:

```bash
opencode plugin opencode-simflow --global
```

Update an existing installation:

```bash
opencode plugin opencode-simflow --global --force
```

The plugin adds the canonical SimFlow skills and two MCP servers without
changing OpenCode permissions or provider configuration. Ask OpenCode to use
the `simflow` skill, a domain skill such as `simflow-vasp`, or describe the
simulation task naturally.

See [OpenCode Quick Start](docs/quickstart_opencode.md) for local development,
validation, conflict handling, and Python interpreter details.

Developer checkout and maintainer build details are covered in the
[Installation Guide](docs/installation.md).

## Project Structure

```
simflow/
├── .opencode/plugins/         # OpenCode project-local loader
├── opencode/                  # Canonical OpenCode plugin module
├── skills/                    # Workflow-layer skills and Domain Assistants
├── workflow/                  # Stage, recipe, gate, policy definitions
│   ├── stages/                # Research intent contracts
│   ├── recipes/               # Optional JSON reference recipes
│   └── gates/                 # Verification and approval gates
├── mcp/                       # MCP servers and connectors
│   ├── servers/
│   │   ├── simflow_state/     # Workflow state management
│   │   └── hpc/               # SLURM, PBS, SSH, Local
│   └── shared/                # MCP transport and shared protocol helpers
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
| `SIMFLOW_PYTHON` | Python executable used by the OpenCode MCP adapter |

Without `S2_API_KEY`, literature search uses OpenAlex. Mock literature results
are only a degraded fallback and are tagged `mock_unverified` with
`usable_as_evidence=false`.

SSH-backed HPC calls pass a required `host` plus optional `user` and `port` in
the per-call `target` object. A bare host may be an OpenSSH alias, hostname, or
IP address. Omitted user and port values are left for OpenSSH configuration to
resolve. Passwords, private keys, key paths, and arbitrary SSH options are not
accepted in MCP payloads; authentication remains host-managed.

## Documentation

- [Claude Code Quick Start](docs/quickstart_claude.md)
- [Codex 快速上手](docs/quickstart_codex.md)
- [OpenCode Quick Start](docs/quickstart_opencode.md)
- [Installation Guide](docs/installation.md)
- [User Guide](docs/user_guide.md)
- [Technical Design](docs/technical-design.md)
- [Workflow Design](docs/workflow-layer-design.md)
- [Skill Design](docs/skill-design.md)
- [MCP Design](docs/mcp-design.md)
- [HPC Integration](docs/hpc-integration.md)
- [Custom Skills](docs/custom-skills.md)
- [Credentials Policy](docs/credentials-policy.md)
- [Current Limitations](docs/current-limitations.md)
- [Release Checklist](docs/release-checklist.md)
- [Docs Index](docs/README.md)

## License

MIT
