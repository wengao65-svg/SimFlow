# SimFlow Installation Guide

SimFlow is distributed to users as Codex and Claude Code plugins. It is not a
primary command-line workflow executor, and the source checkout is mainly for
development, validation, and marketplace publishing.

## System Requirements

| Requirement | Minimum | Recommended |
| --- | --- | --- |
| Python | 3.10 | 3.12+ |
| Node.js | 18 for repository validation | 20+ |
| OS | Linux, macOS, WSL2 | Linux or WSL2 |
| Git | 2.0 | latest |

The runtime, MCP servers, and bundled skill helper scripts use the Python
standard library by default. Optional scientific Python packages are only needed
for engine-specific helper features.

## Install For Codex Users

Install the published Codex marketplace branch:

```bash
codex plugin marketplace add wengao65-svg/SimFlow --ref codex-marketplace
codex
```

Then install and enable `simflow` from Codex:

```text
/plugins
```

Verify that SimFlow is available:

```text
/mcp
$simflow
```

Update the marketplace when a new SimFlow version is published:

```bash
codex plugin marketplace upgrade simflow-marketplace
```

Restart Codex or open a new thread after upgrading.

## Install For Claude Code Users

Install the published Claude marketplace branch:

```bash
claude plugin marketplace add wengao65-svg/SimFlow@claude-marketplace
claude plugin install simflow@simflow-claude-marketplace
```

For a git URL, use Claude's `#ref` syntax:

```bash
claude plugin marketplace add https://github.com/wengao65-svg/SimFlow.git#claude-marketplace
claude plugin install simflow@simflow-claude-marketplace
```

Verify typical skill names:

```text
/simflow:simflow
/simflow:simflow-vasp
/simflow:simflow-cp2k
/simflow:simflow-writing
```

## Developer Source Checkout

Use the source checkout when developing SimFlow, validating release candidates,
or building marketplace wrappers:

```bash
git clone https://github.com/wengao65-svg/SimFlow.git ~/simflow
cd ~/simflow
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
npm install
```

Local Codex wrapper install:

```bash
npm run install:codex
codex
```

Local Claude wrapper install:

```bash
npm run build:claude-marketplace
claude plugin marketplace add ./dist/claude-marketplace
claude plugin install simflow@simflow-claude-marketplace
```

## Optional Python Dependencies

The plugin core does not require scientific Python packages. Install optional
dependencies only when you want local helper scripts to use those libraries:

```bash
pip install -e ".[vasp]"       # pymatgen-backed VASP helpers
pip install -e ".[lammps]"     # MDAnalysis-backed LAMMPS analysis helpers
pip install -e ".[structure]"  # pymatgen and ASE structure helpers
pip install -e ".[all]"        # all optional scientific helpers
```

QE and Gaussian skills are reserved placeholders in the current product build.
Do not advertise `.[qe]` or `.[gaussian]` as supported install extras until
those helpers have product support and release tests.

PyPI distribution is not the current primary user install path. Do not document
or rely on a direct PyPI package install as the release path until a PyPI
release has been published and verified.

## Validation

Validate the source checkout:

```bash
python -m pytest tests/ -q
npm run validate:all
python scripts/audit_skill_scripts.py
```

Validate marketplace wrappers:

```bash
npm run build:codex-marketplace
SIMFLOW_MARKETPLACE_ROOT=dist/codex-marketplace npm run validate:plugin

npm run build:claude-marketplace
SIMFLOW_CLAUDE_MARKETPLACE_ROOT=dist/claude-marketplace npm run validate:claude-plugin
```

Smoke-test MCP startup from the source checkout:

```bash
npm run validate:plugin
npm run validate:claude-plugin
```

These validators initialize the configured SimFlow MCP servers over stdio and
verify `tools/list` responses.

## Runtime Layout

Current source layout:

```text
simflow/
├── skills/                    # Workflow-layer and domain helper skills
├── workflow/                  # Stage, recipe, gate, and policy definitions
├── mcp/                       # MCP servers and connectors
├── runtime/
│   ├── simflow_core/          # State, artifacts, checkpoints, gates, status
│   └── simflow_helpers/       # Optional literature, modeling, compute, engine helpers
├── templates/                 # Optional helper templates
├── schemas/                   # JSON schemas
├── tests/                     # Unit, MCP, and E2E tests
├── docs/                      # User, release, and developer documentation
└── scripts/                   # Validation, scaffold, and marketplace scripts
```

Legacy runtime library and script directories are not current public entry
points.

## Configuration

| Variable | Purpose |
| --- | --- |
| `MP_API_KEY` | Materials Project API key |
| `S2_API_KEY` | Semantic Scholar API key |
| `SIMFLOW_SSH_HOST` | SSH HPC host |
| `SIMFLOW_SSH_USER` | SSH username |
| `SIMFLOW_SSH_KEY` | SSH key file path |
| `SIMFLOW_HPC_HOST` | Optional HPC host alias for helper scripts |
| `SIMFLOW_HPC_BASE` | Optional remote working directory |
| `SIMFLOW_PARTITION` | Optional scheduler partition |
| `SIMFLOW_NTASKS` | Optional MPI task count |

Credentials may be read from the environment but must not be written to
`.simflow/`, artifacts, reports, checkpoints, logs, or handoff packages.

## Troubleshooting

### MCP servers do not appear

Run source validation:

```bash
npm run validate:plugin
npm run validate:claude-plugin
```

Check that the installed plugin contains:

```text
skills/
mcp/
runtime/
workflow/
schemas/
scripts/start_mcp_server.py
```

### Optional scientific helper fails to import a package

Install the relevant optional dependency in the environment where the helper is
running:

```bash
pip install -e ".[all]"
```

### HPC or remote submit is blocked

This is expected unless dry-run evidence, credential scan, matching hashes, and
an explicit `hpc_submit` approval decision are present. Local execution is also
approval-gated.

### Remove project state

SimFlow stores per-project workflow state in `.simflow/`. Delete that directory
only when you intentionally want to remove local workflow state.
