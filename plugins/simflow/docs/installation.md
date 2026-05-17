# SimFlow Installation Guide

## System Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Python | 3.10 | 3.12+ |
| Node.js | 18 (optional, for schema validation) | 20+ |
| OS | Linux, macOS, WSL2 | Linux |
| Git | 2.0 | latest |

SimFlow is a pure Python package with no compiled extensions. It runs on any platform with Python 3.10+.

## Dependencies

### Core (no extra install needed)

SimFlow core has **zero external dependencies** — the runtime, template engine, state management, parsers, and MCP servers use only the Python standard library.

| Component | Dependencies |
|-----------|-------------|
| `runtime/lib/` (state, checkpoint, gates, template, parsers) | stdlib only |
| `mcp/servers/` (literature, structure, hpc, state) | stdlib only |
| `skills/` (CLI scripts) | stdlib only |
| Schema validation | Node.js + `ajv` (dev only) |

### Optional (per software package)

Install optional dependencies based on which simulation software you use:

```bash
# VASP support (pymatgen for structure manipulation)
pip install "simflow[vasp]"

# Quantum ESPRESSO support
pip install "simflow[qe]"

# LAMMPS support (MDAnalysis for trajectory analysis)
pip install "simflow[lammps]"

# Gaussian support
pip install "simflow[gaussian]"

# Structure building (pymatgen + ASE)
pip install "simflow[structure]"

# All software packages
pip install "simflow[all]"

# Development (all + testing tools)
pip install "simflow[dev]"
```

### Optional dependency details

| Package | Version | Used by | Purpose |
|---------|---------|---------|---------|
| `pymatgen` | >=2023.0 | VASP, QE, Gaussian, structure | Crystal structure manipulation, VASP input generation |
| `MDAnalysis` | >=2.5 | LAMMPS, trajectory analysis | RDF, MSD, trajectory parsing |
| `ase` | >=3.22 | structure | Alternative structure builder |
| `pytest` | >=7.0 | dev | Test runner |

## Installation Methods

### Method 1: pip install (recommended)

```bash
# Basic install (core only)
pip install simflow

# With specific software support
pip install "simflow[vasp]"
pip install "simflow[all]"

# Development install (editable)
git clone https://github.com/<your-org>/simflow.git
cd simflow
pip install -e ".[dev]"
```

### Method 2: From source

```bash
git clone https://github.com/<your-org>/simflow.git
cd simflow

# Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate

# Install in editable mode
pip install -e ".[dev]"

# Install Node.js dependencies (optional, for schema validation)
npm install
```

### Method 3: Claude Code plugin

SimFlow also ships a Claude Code adapter as a separate distribution layer from the Codex marketplace. Install the published Claude marketplace branch with Claude's ref syntax:

```bash
claude plugin marketplace add <org>/simflow@claude-marketplace
claude plugin install simflow@simflow-claude-marketplace
```

For a git URL, use `#ref`:

```bash
claude plugin marketplace add https://github.com/<org>/simflow.git#claude-marketplace
claude plugin install simflow@simflow-claude-marketplace
```

For local testing from a source checkout:

```bash
npm run build:claude-marketplace
claude plugin marketplace add ./dist/claude-marketplace
claude plugin install simflow@simflow-claude-marketplace
```

Claude plugin skills are namespaced, for example `/simflow:simflow`, `/simflow:simflow-vasp`, `/simflow:simflow-cp2k`, and `/simflow:simflow-writing`. `claude plugin marketplace add` supports `--scope` and `--sparse`; it does not use a `--ref` option.

## Verification

### Run the test suite

```bash
# All tests (309 tests, ~3 seconds)
python -m pytest tests/ -v

# CP2K-specific tests
python -m pytest tests/runtime/test_cp2k_input.py tests/runtime/test_cp2k_parser.py -v

# VASP-specific tests
python -m pytest tests/runtime/test_vasp_*.py -v

# MCP server tests
python -m pytest tests/mcp/ -v

# E2E workflow tests
python -m pytest tests/e2e/ -v
```

### Validate project structure

```bash
# Requires Node.js
npm install
npm run validate:all
```

### Quick smoke test

```python
from lib.cp2k_input import generate_input, read_cif_to_xyz
from lib.parsers.cp2k_parser import CP2KParser
from lib.template import render_string
from lib.state import init_workflow

# Generate a CP2K input
inp = generate_input({"steps": 10}, "aimd_nvt")
assert "STEPS 10" in inp

# Render a template
result = render_string("Hello {{ name }}", {"name": "SimFlow"})
assert result == "Hello SimFlow"

print("SimFlow OK")
```

## Configuration

### Environment Variables

| Variable | Required | Purpose | Example |
|----------|----------|---------|---------|
| `SIMFLOW_HPC_HOST` | For HPC | SSH host alias | `hpc` |
| `SIMFLOW_HPC_BASE` | For HPC | Remote working directory | `simflow/jobs` |
| `SIMFLOW_CP2K_ENV` | For CP2K | Path to CP2K env.sh on HPC | `source $CP2K_ROOT/env.sh` |
| `SIMFLOW_CP2K_EXE` | For CP2K | CP2K executable path on HPC | `cp2k.psmp` |
| `SIMFLOW_VASP_ENV` | For VASP | Path to VASP env.sh on HPC | `source $VASP_ROOT/env.sh` |
| `SIMFLOW_PARTITION` | For SLURM | SLURM partition name | `cpu` |
| `SIMFLOW_NTASKS` | For SLURM | Number of MPI tasks | `32` |
| `MP_API_KEY` | Optional | Materials Project API key | `your-api-key` |
| `S2_API_KEY` | Optional | Semantic Scholar API key | `your-api-key` |

Missing optional credentials gracefully fall back to mock/dry-run mode.

### HPC SSH Setup

SimFlow uses SSH to connect to HPC clusters. Configure your `~/.ssh/config`:

```
Host hpc
    HostName your-cluster.example.com
    User your-username
    IdentityFile ~/.ssh/id_rsa
    ForwardAgent no
```

Test connectivity:

```bash
ssh hpc hostname
```

### CP2K Setup Example

```bash
# On HPC: CP2K should be installed and accessible
# Set environment variables locally:
export SIMFLOW_HPC_HOST="hpc"
export SIMFLOW_HPC_BASE="simflow/cp2k_jobs"
export SIMFLOW_CP2K_ENV="source $CP2K_ROOT/scripts/env.sh"
export SIMFLOW_CP2K_EXE="$CP2K_ROOT/bin/cp2k.psmp"
export SIMFLOW_PARTITION="cpu"
export SIMFLOW_NTASKS="64"

# Test CP2K workflow (dry run)
python examples/h2o/run_cp2k_workflow.py --dry-run
```

### VASP Setup Example

```bash
export SIMFLOW_HPC_HOST="hpc"
export SIMFLOW_HPC_BASE="simflow/vasp_jobs"
export SIMFLOW_VASP_ENV="source $VASP_ROOT/env.sh"
export SIMFLOW_PARTITION="gpu"
export SIMFLOW_NTASKS="16"
```

## Project Structure

```
simflow/
├── runtime/                   # Core libraries
│   ├── lib/
│   │   ├── cp2k_input.py      # CP2K input generation
│   │   ├── parsers/           # Output parsers (CP2K, VASP)
│   │   ├── state.py           # Workflow state management
│   │   ├── template.py        # Template rendering engine
│   │   ├── gates.py           # Verification gate engine
│   │   ├── artifact.py        # Artifact tracking
│   │   └── checkpoint.py      # Checkpoint/recovery
│   └── scripts/               # CLI scripts
├── skills/                    # Skill definitions (23 skills)
├── templates/                 # Input templates (VASP, CP2K, QE, LAMMPS, SLURM)
├── mcp/                       # MCP servers and connectors
├── workflow/                  # Stage, gate, policy definitions
├── tests/                     # Test suite (309 tests)
├── docs/                      # Documentation
├── examples/                  # Example workflows
├── schemas/                   # JSON schemas
└── scripts/                   # Utility scripts
```

## Troubleshooting

### ImportError: No module named 'lib'

SimFlow's `runtime/lib/` is not on the Python path by default. Either:

```bash
# Option 1: Install in editable mode
pip install -e .

# Option 2: Add to path in your script
import sys
sys.path.insert(0, "runtime")
```

### SSH connection failed

```bash
# Test SSH connectivity
ssh -o ConnectTimeout=10 hpc hostname

# Check SSH config
cat ~/.ssh/config | grep -A5 "Host hpc"

# Verify key permissions
chmod 600 ~/.ssh/id_rsa
```

### Tests failing

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run with verbose output
python -m pytest tests/ -v --tb=long

# Run specific test file
python -m pytest tests/runtime/test_cp2k_input.py -v
```

### pymatgen/MDAnalysis not found

```bash
# Install optional dependencies
pip install "simflow[all]"

# Or install individually
pip install pymatgen MDAnalysis ase
```

### Node.js validation fails

```bash
# Install Node.js dependencies
npm install

# Run validation separately
npm run validate:plugin
npm run validate:skills
npm run validate:schemas
```

## Upgrading

```bash
# pip install
pip install --upgrade simflow

# From source
cd simflow
git pull
pip install -e ".[dev]"
```

## Uninstalling

```bash
pip uninstall simflow
```

SimFlow stores per-project state in `.simflow/` — delete this directory to remove all workflow data.
