# Target Repository Structure

This document describes the current workflow-layer shape. It is not a central
executor design and does not define a fixed DFT/AIMD/MD DAG.

## Top-Level Layout

```text
simflow/
  AGENTS.md
  README.md
  skills/
  workflow/
    stages/
    recipes/
    workflows/
    gates/
    policies/
    templates/
  runtime/
    lib/
    scripts/
  mcp/
    servers/
    shared/
  schemas/
  templates/
  docs/
  tests/
  scripts/
```

## Skills

Canonical workflow-layer skills are:

```text
simflow
simflow-literature-review
simflow-proposal
simflow-modeling
simflow-computation
simflow-analysis-visualization
simflow-writing
simflow-safety-gates
```

Compatibility entries such as `simflow-literature`, `simflow-compute`,
`simflow-analysis`, `simflow-visualization`, `simflow-input-generation`,
`simflow-pipeline`, and `simflow-stage` may remain so older projects and users
do not break. They must describe themselves as compatibility helpers and should
map to the canonical stage vocabulary instead of defining a separate mandatory
workflow path.

Engine skills such as `simflow-vasp`, `simflow-cp2k`, `simflow-qe`,
`simflow-lammps`, and `simflow-gaussian` are domain assistants. They may provide
templates, checks, troubleshooting, and artifact registration guidance. They do
not own workflow progression and must not make helper scripts the only valid
path.

## Workflow Definitions

Canonical top-level stages live in `workflow/stages/`:

```text
literature_review
proposal
modeling
computation
analysis_visualization
writing
```

Legacy alias stages remain available for migration and compatibility:

```text
literature
review
input_generation
compute
analysis
visualization
```

`input_generation` is an optional activity inside `computation`.
`visualization` is an optional activity inside `analysis_visualization`.
`review` is a cross-stage checking action.

Reference recipes live in `workflow/recipes/` and use JSON in this refactor:

```text
dft.json
aimd.json
classical_md.json
phonon.json
neb.json
custom.json
```

Legacy workflow files remain under `workflow/workflows/`:

```text
dft.json
aimd.json
md.json
```

These files are retained as legacy recipe sources for `runtime.lib.workflow`
and migration tests. They are not the canonical workflow contract and should
not be treated as a required executor DAG.

## Runtime

`runtime/lib/` contains state, artifact, checkpoint, lineage, gate, migration,
and optional helper libraries. Engine-specific helpers may suggest and validate,
but they should return uncertainty for unknown tasks instead of forcing a
default calculation.

Legacy runtime CLI wrappers have been removed from the source package. Runtime
entry points should be exposed through skills, MCP tools, or reusable helpers
under `runtime/simflow_helpers/`.

## MCP

MCP servers provide recording and bounded helper tools:

```text
simflow_state
artifact_store
checkpoint_store
literature
structure
hpc
parsers
```

MCP tools must keep `project_root` separate from plugin root. Write tools should
record state, artifacts, lineage, checkpoints, gates, or handoff summaries. They
should not decide the scientific path for the host agent.

## Project State

Per-project state belongs under the user's project root:

```text
.simflow/
  state/
  artifacts/
  checkpoints/
  reports/
  logs/
  extensions/
```

The repository `.gitignore` ignores `.simflow/` because it is runtime state, not
plugin source.
