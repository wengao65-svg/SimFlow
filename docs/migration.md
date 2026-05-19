# Migration Plan

## Goal

The migration moves SimFlow from fixed DFT/AIMD/MD workflows toward an open
workflow layer. Existing projects and helpers should keep working while new
projects use stage intent, recipes, artifact lineage, and evidence-based gates.

## Workflow Migration

Legacy workflow files under `workflow/workflows/` are treated as recipe sources.
The new recipe directory uses JSON:

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

Existing engine and stage skills remain available during migration, but they
are treated as helpers. Canonical workflow behavior moves to the core skills:

- `simflow`
- `simflow-literature-review`
- `simflow-proposal`
- `simflow-modeling`
- `simflow-computation`
- `simflow-analysis-visualization`
- `simflow-writing`
- `simflow-safety-gates`

Legacy helper docs should state that they are optional assistants and not the
canonical workflow contract.

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

The migration CLI is intentionally small and state-oriented:

```text
simflow inspect-legacy --project-root /path/to/project
simflow migrate --project-root /path/to/project
simflow convert-workflow workflow/workflows/dft.json --output /tmp/dft.recipe.json
```

`inspect-legacy` only reports legacy files and stage mapping. `migrate` writes
canonical `.simflow/state/*.json` files and `.simflow/reports/migration.*` while
leaving legacy files in place. `convert-workflow` converts a legacy workflow JSON
definition into an open recipe record without changing project state.

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
