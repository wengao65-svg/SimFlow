# Migration Plan

## Goal

The migration moves SimFlow from fixed DFT/AIMD/MD workflows toward an open
workflow layer. Existing projects and helpers should keep working while new
projects use stage intent, recipes, artifact lineage, and evidence-based gates.

## Workflow Migration

The repository no longer bundles legacy DFT/AIMD/MD workflow JSON under
`workflow/workflows/`. Migration helpers still understand user-provided legacy
workflow definitions and convert them into recipe/tag records. The canonical
recipe directory uses JSON:

```text
workflow/recipes/
  dft.json
  aimd.json
  classical_md.json
  phonon.json
  neb.json
  custom.json
```

Legacy fields map as follows:

| Legacy concept | New concept |
| --- | --- |
| `workflow_type: dft` | `recipe: dft`, optional tag |
| `workflow_type: aimd` | `recipe: aimd`, optional tag |
| `workflow_type: md` | `recipe: classical_md`, optional tag |
| `input_generation` stage | activity inside `computation` |
| `compute` stage | `computation` |
| `analysis` + `visualization` | `analysis_visualization` |
| `review` stage | cross-stage review action |

## Skill Migration

Engine skills remain available during migration, but they are treated as
optional domain assistants. Legacy executor and alias skill entries such as
`simflow-pipeline`, `simflow-stage`, `simflow-compute`, and
`simflow-input-generation` are no longer packaged as skill entry points.
Canonical workflow behavior lives in the core skills:

- `simflow`
- `simflow-literature-review`
- `simflow-proposal`
- `simflow-modeling`
- `simflow-computation`
- `simflow-analysis-visualization`
- `simflow-writing`
- `simflow-safety-gates`

Legacy helper code may remain temporarily for tests or migration adapters, but
new user-facing workflows should enter through the canonical skills.

## State Migration

Existing `.simflow/state` data should be read without deletion. Migration tools
should preserve:

- workflow identifiers
- current stage status
- artifact metadata
- checkpoint records
- job records
- dry-run reports
- handoff notes

New state files may add project, gate, and lineage records, but migration must
not delete legacy state unless the user explicitly requests cleanup.

Migration is currently exposed through runtime library/MCP integration rather
than the removed legacy CLI script surface. Callers should use
`runtime.simflow_core.migration` and state/artifact/checkpoint helpers to
inspect, migrate, or convert user-provided legacy data. Conceptually, migration
still performs these operations:

```text
inspect legacy project state under a project_root
migrate legacy .simflow/state records into canonical state files
convert a user-provided legacy workflow JSON definition into an open recipe
```

Inspection only reports legacy files and stage mapping. Migration writes
canonical `.simflow/state/*.json` files and `.simflow/reports/migration.*` while
leaving legacy files in place. Workflow conversion creates an open recipe record
without changing project state.

## Test Migration

Tests should keep safety, state, artifact, checkpoint, and lineage guarantees.
Tests that previously required fixed parser scripts, fixed report filenames, or
fixed DFT/AIMD/MD DAG execution should become recipe or scenario tests.

Safety tests must remain strict:

- no approval means no real submit
- local submit also requires approval
- missing dry-run evidence blocks submit
- missing or failing credential scan blocks or warns according to policy
- changed job script or input hash invalidates approval
- missing `project_root` blocks write operations
