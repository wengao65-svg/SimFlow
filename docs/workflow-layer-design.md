# Workflow Layer Design

## Positioning

SimFlow is a computational simulation workflow layer for agentic coding
systems. It is not a centralized workflow executor and it does not decide the
science for Codex, Claude Code, or another host agent.

The host agent is responsible for reasoning, literature search, modeling,
coding, analysis, and writing. SimFlow provides the evidence layer around that
work:

- research-stage semantics
- `.simflow/` state records
- artifact metadata and lineage
- checkpoints at stage boundaries
- safety gates for risky actions
- handoff notes between stages or agents

SimFlow borrows the discipline of skill-first, plan-first, and
verify-before-completion workflows, but it does not depend on Superpowers and
does not require the Superpowers runtime or directory layout.

## Hard And Soft Constraints

SimFlow keeps hard constraints only where safety or traceability requires them:

- `.simflow/` is the project workflow state root
- artifacts must include metadata and lineage
- stage boundaries must create checkpoints
- real local, remote, or HPC execution requires approval
- compute work is dry-run first
- credentials must not be stored in state, artifacts, reports, or logs
- incomplete calculations must not be recorded as completed results
- literature, data, figures, and citations must not be fabricated

Other guidance is intentionally soft:

- recommended stages
- suggested checks
- recommended skills
- example recipes
- handoff notes
- artifact suggestions

The host agent may choose different literature sources, modeling tools,
simulation engines, parsers, plotting libraries, or report structures when the
evidence and safety boundaries are still satisfied.

## Stage Model

Stages represent research intent and evidence boundaries, not mandatory executor
nodes. The default top-level stage vocabulary is:

1. `literature_review`
2. `proposal`
3. `modeling`
4. `computation`
5. `analysis_visualization`
6. `writing`

Any stage can be entered independently when its inputs and evidence needs are
satisfied. `input_generation` is treated as an optional activity inside
`computation`; `visualization` is treated as an optional activity inside
`analysis_visualization`; review is a cross-cutting action rather than a fixed
top-level stage.

Stage definitions should guide agents with fields such as:

```json
{
  "id": "computation",
  "intent": "Prepare, validate, optionally run, and record computational simulation jobs.",
  "acceptable_inputs": [
    "user-provided input files",
    "generated input files",
    "model artifacts",
    "calculation plan",
    "previous checkpoint"
  ],
  "evidence_outputs": [
    "calculation_manifest",
    "input_files",
    "input_validation_report",
    "dry_run_report",
    "resource_estimate",
    {"id": "job_record_if_submitted", "required_when": "real_submit_recorded"}
  ],
  "recommended_skills": [
    "simflow-computation",
    "optional engine-specific helper"
  ],
  "suggested_checks": [
    "input completeness",
    "resource reasonableness",
    "software command documented",
    "environment documented",
    "output hashes recorded"
  ],
  "approval_triggers": [
    "real_hpc_submit",
    "remote_execution",
    "local_job_submit",
    "destructive_file_operation",
    "licensed_or_proprietary_file_handling"
  ],
  "handoff_notes": [
    "Record what was run, where it was run, with which inputs, and whether outputs are complete."
  ]
}
```

These fields are contracts for evidence and review. They are not a permission
system that blocks every unlisted scientific path.

## Recipes

DFT, AIMD, classical MD, phonon, NEB, defect, adsorption, and similar workflows
are recipes or tags. They are examples of common computational paths, not
top-level workflow types that limit what an agent may do.

Recipe files should describe a reference path, typical artifacts, common risks,
and recommended checks. They must not prevent custom workflows, unknown
software names, or unlisted analysis scripts when those choices are recorded
with adequate evidence.

Software helper support is resolved by the shared toolchain contract, not by
individual recipe files. Recipes may suggest applicable tools or activity
roles, but they must not define separate support-level fields such as
tracked-only or unsupported software lists.

For the current refactor, recipes use JSON so the project does not add a YAML
runtime dependency.

## State Model

Project state belongs under `.simflow/` in the user's project root:

```text
.simflow/
  state/
    project.json
    workflow.json
    stages.json
    gates.json
    artifacts.json
    lineage.json
    checkpoints.json
  artifacts/
  checkpoints/
  reports/
  logs/
```

The plugin root is only for importing SimFlow code and bundled assets. MCP
servers commonly run from the plugin root, so write tools must receive an
explicit `project_root` and must not infer the project from their own cwd.

## Completion And Handoff

A stage is complete only when the relevant evidence exists, artifacts are
registered, lineage is connected, verification has been recorded, and a
checkpoint exists. Handoff summaries should state:

- current stage and status
- produced artifacts
- latest checkpoint
- unresolved risks or warnings
- next recommended actions
- whether approval is required
