# SimFlow Developer Guide

## Architecture Overview

SimFlow is a Codex-native computational simulation domain workflow layer. It is NOT a standalone CLI tool — it operates as a plugin within the Codex/OMX ecosystem.

```
User
  -> Skills (entry point, SKILL.md)
  -> Workflow Layer (stages, gates, policies)
  -> MCP Servers (tool interfaces)
  -> Runtime (Python lib + scripts)
  -> .simflow/ (state, artifacts, checkpoints)
```

## Directory Structure

```
simflow/
├── .codex-plugin/       # Plugin metadata
│   └── plugin.json      # Plugin configuration
├── .codex/              # Codex configuration
│   ├── config.toml      # Default settings
│   └── hooks.json       # Hook definitions
├── skills/              # Skill definitions (SKILL.md)
│   ├── simflow/         # Main entry skill
│   ├── simflow-intake/  # Intake skill
│   ├── simflow-plan/    # Planning skill
│   ├── simflow-pipeline/# Pipeline orchestration
│   ├── simflow-stage/   # Single stage execution
│   ├── simflow-literature/  # Literature stage
│   ├── simflow-review/      # Review stage
│   ├── simflow-proposal/    # Proposal stage
│   ├── simflow-modeling/    # Modeling stage
│   ├── simflow-input-generation/ # Input generation
│   ├── simflow-compute/     # Compute preparation
│   ├── simflow-analysis/    # Analysis stage
│   ├── simflow-visualization/ # Visualization
│   ├── simflow-writing/     # Writing stage
│   ├── simflow-vasp/        # VASP-specific
│   ├── simflow-qe/          # QE-specific
│   ├── simflow-lammps/      # LAMMPS-specific
│   └── simflow-gaussian/    # Gaussian-specific
├── agents/              # Agent role definitions
├── workflow/            # Workflow definitions
│   ├── stages/          # Stage configs (JSON)
│   ├── workflows/       # Workflow configs (JSON)
│   ├── gates/           # Approval gates (JSON)
│   ├── policies/        # Execution policies (JSON)
│   └── templates/       # Dry-run templates
├── mcp/                 # MCP tool servers
│   ├── servers/         # Server implementations
│   └── shared/          # Shared utilities
├── runtime/             # Python runtime
│   ├── lib/             # Core library
│   │   ├── state.py     # State management
│   │   ├── artifact.py  # Artifact management
│   │   ├── checkpoint.py # Checkpoint management
│   │   ├── validator.py # Validation utilities
│   │   ├── parser.py    # Base parser interface
│   │   └── parsers/     # Software parsers
│   └── scripts/         # Executable scripts
├── schemas/             # JSON schemas
├── hooks/               # Hook documentation
├── notifications/       # Notification templates
├── templates/           # .simflow templates
├── tests/               # Test suite
└── scripts/             # Dev scripts
```

## Key Design Decisions

### 1. Skill-First Architecture

All user interactions enter through skills. Skills are the only entry point — there is no CLI, no REST API, no direct function calls. This keeps the interface clean and composable.

### 2. Declarative Workflow

Workflows are defined as JSON files with explicit stages, dependencies, validators, and gates. The workflow engine reads these definitions and enforces them — no workflow logic is hardcoded.

### 3. State in .simflow/

All workflow state lives in a `.simflow/` directory in the project root. This makes it easy to version, inspect, and recover. The state is simple JSON files — no database required.

### 4. MCP for Tool Interfaces

MCP servers provide stable tool interfaces for state management, artifact storage, parsing, and more. Each server is independent and can be developed/tested separately.

### 5. Dry-Run by Default

All compute operations default to dry-run mode. Real HPC submission requires explicit user approval through the approval gate system.

### 6. No LLM Implementation

SimFlow does not implement or configure LLM models. The host (Codex/OMX) handles all inference. SimFlow only provides workflow structure and domain knowledge.

## Adding a New Skill

1. Run `node scripts/scaffold_skill.js my-new-skill`
2. Edit `skills/my-new-skill/SKILL.md`
3. If the skill maps to a workflow stage, create a stage definition:
   `node scripts/scaffold_stage.js my_new_stage`
4. Add the stage to the appropriate workflow in `workflow/workflows/`
5. Run `node scripts/validate_skills.js` to verify

## Adding a New Software Parser

1. Create `runtime/lib/parsers/my_software_parser.py`
2. Extend `BaseParser` and implement `parse()` and `check_convergence()`
3. Register in `mcp/servers/parsers/server.py`
4. Add a software-specific skill: `skills/simflow-my-software/`
5. Add reference parameters: `skills/simflow-my-software/references/`

## Running Tests

```bash
# Validate plugin structure
node scripts/validate_plugin.js

# Validate skills
node scripts/validate_skills.js

# Validate schemas
node scripts/validate_schemas.js

# Run schema tests
node tests/schemas/run_all.js

# Run Python runtime tests
python tests/runtime/test_state.py
python tests/runtime/test_artifact.py
python tests/runtime/test_checkpoint.py
```

## Hook System

Hooks are triggered at specific points in the workflow lifecycle:

| Hook | Trigger | Purpose |
|------|---------|---------|
| pre_stage | Before stage execution | Input validation |
| post_stage | After stage completion | Artifact registration, checkpoint |
| pre_submit | Before HPC submission | Approval gate check |
| post_analysis | After analysis | Convergence check |
| on_error | On failure | Error recovery |
| before_handoff | Before session end | Completeness check |

## Approval Gates

Gates require explicit user approval before proceeding:

| Gate | Trigger | Auto-approve |
|------|---------|-------------|
| hpc_submit | Real HPC submission | No |
| resource_exceeds_budget | Resource estimate too high | No |
| convergence_failure | Calculation not converged | No |
| abnormal_optimization | Structure optimization anomaly | No |
| parameter_adjustment | Input parameters need change | No |
| unexpected_results | Analysis results unexpected | No |
| ambiguous_visualization | Figure interpretation unclear | No |
| structure_adjustment | Manuscript structure needs change | No |
| key_conclusion_review | Key conclusions need review | No |
