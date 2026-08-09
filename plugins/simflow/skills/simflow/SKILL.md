---
name: simflow
description: Route computational simulation research requests into SimFlow's workflow layer; use for top-level stage selection, cross-skill delegation, state/artifact/checkpoint/handoff coordination, safety escalation, and workflow boundary decisions across literature review, proposal, modeling, computation, analysis/visualization, writing, verification, and handoff.
---

# SimFlow Top-Level Router

`simflow` is the top-level router skill for SimFlow. It maps user intent to
canonical stages, recipe/tag metadata, downstream skills, evidence needs, state
write decisions, and safety gates. It is not a centralized workflow executor,
domain parser, input generator, scientific judge, writing authority, submitter,
or approval gate.

Use `router_contract.json` only as a lightweight machine-readable companion for
stable routing categories. It is a contract summary, not a runtime schema and
not a source of software capability support; use the shared toolchain contract
for current helper support levels.

## Purpose

- Choose the appropriate SimFlow stage, recipe/tag, and downstream skill set
  from a computational simulation research request.
- Coordinate evidence, artifact, checkpoint, verification, handoff, and safety
  boundaries without replacing the host agent's scientific reasoning or tools.
- Keep dry-run-first and evidence-first behavior visible whenever real local,
  remote, or HPC execution may be requested.

## Trigger conditions

- The user asks about computational simulation, materials modeling, DFT, AIMD,
  classical MD, MLP-MD, literature review, modeling, computation, analysis,
  visualization, writing, project status, checkpointing, verification, or
  handoff.
- The user wants SimFlow to track state, artifacts, lineage, gates, or recovery
  checkpoints for an open research task.
- Multiple SimFlow skills could apply and a top-level routing decision is
  needed.

## Input conditions

- User intent, available project evidence, current workflow state when present,
  and the explicit `project_root` whenever state access may be needed.
- Optional recipe/tag context, software/toolchain provenance, artifact ids,
  checkpoint references, gate records, or requested deliverables.
- Missing or ambiguous inputs must remain explicit; do not fabricate state,
  artifacts, software support, or scientific evidence to complete a route.

## Stage And Skill Routing

- `literature_review`: route source discovery, screening, notes, and citation
  evidence to `simflow-literature-review`.
- `proposal`: route research plans, assumptions, alternatives, recipes, risks,
  and evidence contracts to `simflow-proposal`.
- `modeling`: route structure/model sources, transformations, supercells,
  constraints, provenance, and validation to `simflow-modeling`.
- `computation`: route input preparation, validation, dry-run plans,
  submit-readiness evidence, approved job records, and user-provided
  computation evidence to `simflow-computation`.
- `analysis_visualization`: route output inspection, data extraction, scripts,
  statistics, figures, visual QA, and source-data lineage to
  `simflow-analysis-visualization`.
- `writing`: route claim maps, drafts, captions, reproducibility packages, and
  evidence-calibrated narratives to `simflow-writing`.

Any stage can be entered directly when the needed evidence exists. Treat DFT,
AIMD, classical MD, MLP-MD, phonon, NEB, defect, adsorption, transport, active
learning, and custom workflows as recipe/tag metadata, not top-level workflow
stages.

## Delegation Rules

- `simflow` owns top-level routing, stage/tag selection, state-write decisions,
  safety escalation detection, and cross-skill boundary resolution.
- Domain skills own software-specific file semantics, task uncertainty,
  documentation pointers, static checks, parser limits, and domain warnings.
  Route VASP, CP2K, LAMMPS, GPUMD/NEP, and MLP-specific questions to
  `simflow-vasp`, `simflow-cp2k`, `simflow-lammps`, `simflow-gpumd`, or
  `simflow-mlp` as appropriate.
- `simflow-computation` owns input-generation stage integration, dry-run plans,
  resource estimates, submit-readiness evidence, computation artifacts, and job
  records after approved real submits.
- `simflow-safety-gates` owns high-risk approval decisions and gate records.
- `simflow-verify` owns evidence sufficiency, readiness checks, and
  verification reports.
- `simflow-handoff` owns transfer summaries, artifact inventories, risks,
  approval needs, and next-step packages.
- `simflow-checkpoint` owns checkpoint creation, inspection, restore integrity,
  and overwrite/rollback confirmation.
- `simflow-writing` owns claim wording, speculation labeling, and
  claim-evidence consistency.
- `simflow` must not become the only executor, parser, validator, plotter,
  report generator, or scientific judge.

## Status write rules

Write `.simflow/` state only when the user asks to initialize, track,
checkpoint, verify, handoff, or record work; when artifacts, inputs, outputs,
scripts, figures, claims, gates, reports, or decisions need metadata and
lineage; or when a stage, failure, approval, or handoff boundary is reached.

Do not write `.simflow/` state for casual conceptual explanation, preliminary
brainstorming without a record request, purely educational discussion, or
route-only answers that do not create artifacts or decisions.

Always use the explicit user project root/current `project_root`. Never write
project state into the plugin root, skill directory, MCP server cwd, tool installation directory, or `.omx/`.

## Directory guidance

When the host agent creates a new stage directory in a user project, follow
the two-layer convention defined in `docs/user-project-layout.md`:

- Top level: `phaseN_<canonical_stage>/` where `phase1`..`phase6` map 1:1
  to the canonical stages `literature_review`..`writing`. Phase numbers are
  fixed and must not be renumbered when a phase is skipped.
- Second level: `stageN_<snake_case_descriptor>/` inside the phase.
  Numbering is local to the phase. One `stageN_*` equals one logical
  sub-activity; variants (temperature, method) belong as subdirectories,
  not as same-prefixed siblings.
- Prep and run must be separated: `dataset_prep/` vs `run_step1/`,
  `run_step2/`. Iteration uses `vN_<desc>_<YYYYMMDD>/`, not bare integers.
- Shared directories (`scripts/`, `reference/`, `config/`, `templates/`,
  `tests/`, `docs/`, `archives/`, `legacy/`, `scratch/`) live at the project
  root. Bare `stageN_*` at the project root is forbidden.
- `.simflow/` lives only at `project_root`; never create a nested
  `.simflow/` inside a phase directory.

Route verification of an existing layout to `simflow-verify`'s Directory
Hygiene Checks.

## Checkpoint rules

- Do not create a checkpoint for route-only or conceptual responses that do not
  establish a workflow boundary.
- Delegate checkpoint creation, inspection, and recovery to
  `simflow-checkpoint`; associate every checkpoint with a workflow and stage.
- Require a checkpoint when a tracked stage boundary is completed and preserve
  failure evidence when a tracked stage cannot proceed.

## Output artifacts

When routing a request, produce or instruct the host agent to produce this
conceptual shape:

```json
{
  "interpreted_intent": "...",
  "recommended_stage": "...",
  "recommended_recipe_tags": [],
  "recommended_skills": [],
  "required_evidence": [],
  "safety_gates": [],
  "state_write_needed": false,
  "state_write_reason": null,
  "next_actions": [],
  "risks_or_uncertainties": []
}
```

This is a router output contract, not a mandatory runtime schema.

## Optional End-To-End Research Workflow Script

When a user wants to drive the full canonical chain
`literature_review -> proposal -> modeling -> computation -> analysis_visualization -> writing`
from a structured research intent, the optional
`scripts/run_research_workflow.py` skill script initializes research via
`runtime.simflow_helpers.project.intake`, runs the canonical pipeline with
dry-run-first behavior, and emits a compact JSON summary at
`.simflow/reports/research_workflow_summary.json` covering workflow id/status,
completed stages, artifact counts by stage/type, checkpoint summary, computation
dry-run status, `hpc_submit` gate status, handoff report paths, and next
actions. It never submits local, remote, or HPC jobs.

## Safety Escalation

Escalate to `simflow-safety-gates` whenever the request involves real local execution,
remote execution, HPC submit, scheduler interaction, job launch,
`sbatch`, `qsub`, `srun`, `mpirun`, `mpiexec`, SSH, cluster access,
credentials, tokens, private keys, license files, proprietary files, VASP
POTCAR/licensed content, expensive compute, destructive operations, or attempts
to bypass dry-run, hash checks, verification, or approval.

`simflow` may summarize missing evidence and next steps. It must not approve,
execute, submit, access remote systems, handle credentials, or claim gate
passage itself. Real execution and HPC submit remain downstream safety-gated
actions, never router actions.

## Ambiguous Intent Handling

- Return candidate stages, candidate skills, missing information, safe default
  evidence actions, and risks.
- Ask only for information that blocks safe progress or materially changes the
  evidence contract.
- If progress is safe without clarification, proceed with dry-run,
  static-inspection, route-only, or evidence-only planning.
- Do not default unknown software to a supported helper path.
- Do not default unknown computation tasks to static, ENERGY, NVT, training,
  or any other known task.
- Preserve unsupported or unknown tools as provenance and route them to generic
  computation or analysis evidence intake when appropriate.

## Prohibited actions

- Do not perform software-specific input generation, parser-specific output
  interpretation, real simulation execution, local submit, remote execution, HPC
  submit, scheduler interaction, or credential handling from `simflow`.
- Do not make scientific convergence, production-readiness, transferability,
  mechanism, transport-property, or publication claims without evidence.
- Do not fabricate literature, computation results, datasets, figures,
  citations, convergence states, validation status, approval states, completed
  calculations, or job states.
- Do not store credentials or licensed/proprietary file contents in state,
  reports, logs, checkpoints, or handoff packages.
- Do not force fixed parsers, builders, plotting libraries, report names, or
  engine choices as the only valid path.

## Manual confirmation scenarios

- Research goal, stage entry, deliverable format, evidence threshold, or
  approval scope is unclear and affects the plan.
- Real local/remote/HPC execution, scheduler use, licensed/proprietary files,
  credentials, high-cost resources, destructive operations, or state restore is
  involved.
- Evidence is missing, incomplete, stale, contradictory, private, or would be
  interpreted beyond its support.
- Claim strength, production-readiness threshold, active-learning stop criteria,
  analysis method, or figure interpretation materially affects a scientific
  conclusion.

## Required MCP Engagement

This skill requires the following MCP tool engagement when loaded:

- **Minimum engagement**: Call `simflow_state/read_state` before any state-write
  tool (`simflow_state/register_artifact`, `simflow_state/create_checkpoint`, `update_stage`,
  `record_*_evidence`, `write_state`).
- **Task-shape-aware engagement**: All task shapes — including single-stage
  compute tasks (GPUMD compile, VASP relax, NEP training) — must engage at least
  one SimFlow MCP tool. The router must suggest MCP engagement for every task,
  not only multi-stage research tasks.
- **Engagement contract enforcement**: State-write MCP tools are hard-blocked
  unless `read_state` was called in the same session (30-min timeout). Calling
  any read-only tool (workflow_status, stage_readiness, etc.) auto-satisfies
  this prerequisite.

## Quick Start for Re-entering a Project

When entering a project that already has a `.simflow/` directory:

1. Call `simflow_state/read_state` (or `workflow_status`) to load current state
2. Do NOT call `init_workflow` — it is idempotent and will just return existing
   state without changes
3. Call `simflow_state/session_handoff` for a compact state summary
4. Call `simflow_state/orphan_compute_scanner` if you suspect unregistered compute
5. Proceed with your task — state-write tools will work because read_state was
   called in step 1
