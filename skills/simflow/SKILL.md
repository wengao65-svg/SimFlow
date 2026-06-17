---
name: simflow
description: Route computational simulation research requests into SimFlow's workflow layer; use for top-level stage selection, cross-skill delegation, state/artifact/checkpoint/handoff coordination, safety escalation, and workflow boundary decisions across literature review, proposal, modeling, computation, analysis/visualization, writing, verification, and handoff.
---

# SimFlow Top-Level Routing Contract

`simflow` is the top-level router skill for SimFlow. It maps user intent to
canonical stages, recipe/tag metadata, domain skills, support skills, evidence
requirements, and safety gates. It is not a centralized workflow executor,
domain parser, input generator, scientific judge, writing authority, submitter,
or approval gate.

Use `router_contract.json` as a lightweight machine-readable companion when a
test or tool needs stable routing categories. That file is a contract summary,
not a mandatory runtime schema.

## Purpose

- Interpret computational simulation research intent and choose the appropriate
  SimFlow stage, recipe/tag, and downstream skill set.
- Coordinate evidence, artifact, checkpoint, verification, handoff, and safety
  boundaries without replacing the host agent's scientific reasoning or tools.
- Keep dry-run-first and evidence-first behavior visible whenever real local,
  remote, or HPC execution may be requested.

## Trigger Conditions

- The user asks about computational simulation, materials modeling, DFT, AIMD,
  classical MD, MLP-MD, literature review, modeling, computation, analysis,
  visualization, writing, project status, checkpointing, verification, or
  handoff.
- The user wants SimFlow to track state, artifacts, lineage, gates, or recovery
  checkpoints for an open research task.
- Multiple SimFlow skills could apply and a top-level routing decision is
  needed.

## Input Conditions

- User goal, current stage, available files, requested deliverable, constraints,
  software/toolchain hints, project root, or previous checkpoint.
- Optional literature, structures, input decks, outputs, scripts, figures,
  drafts, validation reports, dry-run evidence, gate records, or environment
  notes.
- If writing state, resolve the explicit user project root/current `project_root`;
  never infer project state from the plugin root, skill directory, MCP server
  cwd, tool installation directory, or `.omx/`.

## Routing Matrix

| User intent | Primary skill | Secondary skills | Stage | Notes |
| --- | --- | --- | --- | --- |
| Literature search or review | `simflow-literature-review` | `simflow-writing`, `simflow-handoff` | `literature_review` | Record source logs, screening, notes, citation evidence, and review limits. |
| Proposal or research plan | `simflow-proposal` | domain skills, `simflow-verify` | `proposal` | Record assumptions, alternatives, recipe tags, resources, risks, and evidence needs. |
| Structure modeling or model preparation | `simflow-modeling` | domain skills, `simflow-verify` | `modeling` | Preserve original models and transformations with lineage. |
| VASP setup, validation, output review | `simflow-vasp` | `simflow-computation`, `simflow-analysis-visualization`, `simflow-safety-gates` | `computation` or `analysis_visualization` | VASP owns file semantics; POTCAR/licensed handling escalates. |
| CP2K setup, validation, output review | `simflow-cp2k` | `simflow-computation`, `simflow-analysis-visualization`, `simflow-safety-gates` | `computation` or `analysis_visualization` | CP2K owns input/output semantics and official-source context. |
| LAMMPS setup, validation, output review | `simflow-lammps` | `simflow-computation`, `simflow-analysis-visualization`, `simflow-safety-gates` | `computation` or `analysis_visualization` | Track force-field provenance, MD controls, logs, dumps, and statistics. |
| GPUMD/NEP setup, validation, dry-run planning, selected parsing | `simflow-gpumd` | `simflow-computation`, `simflow-mlp`, `simflow-safety-gates` | `computation` or `analysis_visualization` | GPUMD/NEP are helper-supported only for bounded preparation, validation, planning, selected parsing, orchestration, and evidence recording. |
| MLP dataset, training evidence, production-readiness review | `simflow-mlp` | domain skills, `simflow-verify`, `simflow-writing`, `simflow-safety-gates` | `proposal`, `computation`, `analysis_visualization`, or `writing` | Scientific readiness is not submit permission. |
| Real local execution, remote execution, or HPC submit | `simflow-computation` | `simflow-safety-gates`, domain skills, `simflow-verify`, `simflow-checkpoint` | `computation` | Require dry-run, validation, resource estimate, credential scan, hashes, and approval evidence. |
| Data analysis, figure generation, visualization | `simflow-analysis-visualization` | domain skills, `simflow-writing`, `simflow-verify` | `analysis_visualization` | Record scripts, source data, derived data, visual QA, and figure lineage. |
| Manuscript writing or claim drafting | `simflow-writing` | `simflow-verify`, `simflow-handoff`, prior-stage skills | `writing` | Calibrate claims to evidence and label speculation or missing evidence. |
| Project status, checkpoint, handoff, verification | `simflow-verify`, `simflow-checkpoint`, or `simflow-handoff` | relevant stage/domain skills | current stage | Use read-only status when possible; write state only for reports, checkpoints, or handoff packages. |
| Unknown or unsupported software evidence intake | `simflow-computation` or `simflow-analysis-visualization` | `simflow-verify`, `simflow-handoff` | stage matching evidence role | Record provenance and limitations; do not force unknown tools into supported helper paths. |

## Delegation Rules

- `simflow` owns top-level routing, stage/tag selection, state-write decisions,
  safety escalation detection, and cross-skill boundary resolution.
- Domain skills own software-specific file semantics, task uncertainty,
  documentation pointers, static checks, parser limits, and domain warnings.
- `simflow-computation` owns input-generation stage integration, dry-run plans,
  resource estimates, submit-readiness evidence, computation artifacts, and job
  records after approved real submits.
- `simflow-safety-gates` owns high-risk approval decisions and gate records.
- `simflow-verify` owns evidence sufficiency, readiness checks, and verification
  reports.
- `simflow-handoff` owns transfer summaries, artifact inventories, next-step
  packages, and session-end context.
- `simflow-checkpoint` owns checkpoint creation, inspection, restore integrity,
  and overwrite/rollback confirmation.
- `simflow-writing` owns claim wording, manuscript drafting, speculation
  labeling, and claim-evidence consistency.
- `simflow-analysis-visualization` owns data intake, analysis scripts, figure
  QA, plotting routes, derived data, and source-data lineage.
- `simflow` must not become the only executor, parser, validator, plotter,
  report generator, or scientific judge.

## Canonical Stage Selection

- `literature_review`: source discovery, screening, notes, citation evidence,
  literature synthesis, and source-backed review claims.
- `proposal`: research plan, assumptions, alternatives, recipe/tag selection,
  resources, risks, and evidence contract.
- `modeling`: structure/model sources, transformations, supercells,
  constraints, provenance, and model validation.
- `computation`: input preparation, static validation, dry-run planning,
  resource estimate, submit-readiness evidence, and approved job records.
- `analysis_visualization`: output inspection, data extraction, statistics,
  figures, visual QA, interpretation notes, and analysis lineage.
- `writing`: claim maps, drafts, methods/results text, captions,
  reproducibility packages, and evidence-calibrated narratives.

Any stage can be entered directly when the needed evidence exists.

## Recipe / Tag Selection

- Treat DFT, AIMD, classical MD, MLP-MD, phonon, NEB, defect, adsorption,
  transport, active learning, and custom workflows as recipe/tag metadata, not
  top-level stage replacements.
- Preserve toolchain fields as planning/provenance metadata. They do not block
  generic evidence intake for tracked-only or unknown software.
- When task intent is unknown, return candidate tags and missing information;
  do not default to static, ENERGY, NVT, training, or another common task.

## Domain Skill Routing

- Route VASP-specific inputs/outputs, POTCAR metadata, NEB, phonons, AIMD, SOC,
  hybrid, DFT+U, GW/BSE/RPA, defects, surfaces, and adsorption to
  `simflow-vasp`.
- Route CP2K input decks, GLOBAL/FORCE_EVAL/DFT/MOTION sections, basis/potential
  choices, AIMD, restart, logs, `.ener`, and trajectories to `simflow-cp2k`.
- Route LAMMPS input scripts, data files, logs, dumps, force-field provenance,
  RDF/MSD/diffusion, and MD review to `simflow-lammps`.
- Route GPUMD, NEP, `run.in`, `model.xyz`, `nep.in`, `train.xyz`, `test.xyz`,
  `nep.txt`, `loss.out`, `thermo.out`, and GPUMDkit-adjacent evidence to
  `simflow-gpumd`.
- Route cross-tool MLP dataset, label, training, validation, active-learning,
  anomaly, and production-readiness evidence to `simflow-mlp`.
- Route unsupported or unknown tools to generic computation or analysis
  evidence intake with explicit provenance and limitations.

## State Write Decision

Write `.simflow/` state only when:

- the user asks to initialize, track, checkpoint, verify, handoff, or record;
- an artifact, input, output, script, figure, claim, gate, report, or decision
  needs metadata and lineage;
- a stage boundary, failure boundary, approval boundary, or handoff boundary is
  reached;
- real execution may be planned, approved, denied, or recorded;
- a verification report, checkpoint, gate decision, or handoff package is
  needed.

Do not write `.simflow/` state for:

- casual conceptual explanation;
- preliminary brainstorming unless the user asks to record it;
- purely educational discussion;
- route-only answers that do not create artifacts or decisions.

Always use the explicit user project root/current `project_root`. Never write
project state into the plugin root, skill directory, MCP server cwd, tool
installation directory, or `.omx/`.

## Output Artifacts

- Router summary, stage recommendation, recipe/tag recommendation, required
  evidence list, safety-gate list, state-write decision, risks, and next steps.
- Registered artifacts, checkpoints, verification reports, gate records, handoff
  packages, or helper-run manifests when the routed task writes state.
- User-requested scientific deliverables only when their evidence source,
  assumptions, limitations, and lineage are recorded or clearly stated.

## Standard Router Output

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

This is a router output contract, not a required runtime schema unless a future
implementation explicitly introduces one.

## Safety Escalation

Escalate to `simflow-safety-gates` whenever the request involves:

- real local execution, remote execution, HPC submit, scheduler interaction, or
  job launch;
- commands such as `sbatch`, `qsub`, `srun`, `mpirun`, `mpiexec`, SSH, cluster
  access, module-loaded executables, or equivalent launchers;
- credentials, tokens, private keys, environment secrets, license files,
  proprietary files, private paths, or VASP POTCAR/licensed content;
- expensive compute, destructive operations, overwrites, data deletion, or
  user attempts to bypass dry-run, hash checks, verification, or approval.

`simflow` may summarize missing evidence and next steps. It must not approve,
execute, submit, access remote systems, handle credentials, or claim gate
passage itself.

## Checkpoint Rules

- Create checkpoints at stage boundaries, evidence review boundaries, handoff
  boundaries, high-risk gate boundaries, and failure boundaries.
- Checkpoints must reference workflow/stage/job context, artifact ids, gate
  decisions when relevant, risks, and next actions.
- Do not checkpoint unfinished, unverified, unapproved, waiting, or failed work
  as completed.
- Restore operations belong to `simflow-checkpoint` and require integrity checks
  plus confirmation when current state may be overwritten.

## Verify / Handoff Rules

- Route evidence sufficiency, readiness, missing evidence, stale hash, and stage
  completion checks to `simflow-verify`.
- Route transfer summaries, artifact inventories, latest checkpoint summaries,
  risks, unresolved items, approval needs, and next-step packages to
  `simflow-handoff`.
- Verification failure blocks stage advancement. Handoff must preserve warnings,
  limitations, and unfinished work.

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
- Preserve unsupported or unknown tools as provenance and route to generic
  evidence intake when appropriate.

## Cross-Skill Conflict Rules

- Domain skill owns file semantics.
- Stage skill owns stage evidence boundaries.
- Computation skill owns dry-run and submit-readiness evidence.
- Safety-gates skill owns approval decisions.
- Verify skill owns evidence/readiness evaluation.
- Writing skill owns claim wording and speculation labeling.
- Handoff skill owns transfer packages.
- Checkpoint skill owns restore/checkpoint semantics.
- If skills conflict, prefer the stricter safety, evidence, provenance, and
  claim-calibration boundary.

## Prohibited Actions

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

## Manual Confirmation Scenarios

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

## Examples

| Request | Interpreted intent | Stage | Skills | Evidence needed | Safety gate | Must not do |
| --- | --- | --- | --- | --- | --- | --- |
| "Plan a VASP NEB workflow" | NEB computation planning | `proposal` then `computation` | `simflow-vasp`, `simflow-computation`, `simflow-verify` | endpoints/images, INCAR/KPOINTS/POTCAR metadata, predecessor evidence, dry-run plan | if real run or licensed handling is requested | Do not default to static or submit. |
| "Set up CP2K AIMD" | CP2K input/dry-run planning | `computation` | `simflow-cp2k`, `simflow-computation` | structure, cell, charge, basis/potential choices, ensemble, timestep, resource estimate | if execution or remote target is requested | Do not run CP2K or assume modules exist. |
| "Review this LAMMPS NVT job" | LAMMPS input/log review | `computation` or `analysis_visualization` | `simflow-lammps`, `simflow-analysis-visualization` | input script, data file, force-field provenance, log/dump if present | if rerun/submit is requested | Do not hide force-field gaps or equilibration risk. |
| "Prepare GPUMD/NEP dry-run plan" | GPUMD/NEP helper-supported planning | `computation` | `simflow-gpumd`, `simflow-computation`, `simflow-mlp` | structure or `train.xyz`, potential/model evidence, parameters, validation report | if real `gpumd`/`nep` execution is requested | Do not claim real execution support or production readiness. |
| "Is this MLP ready for production MD?" | MLP evidence/readiness review | `analysis_visualization` | `simflow-mlp`, `simflow-verify`, `simflow-writing` | dataset lineage, labels, splits, metrics, smoke MD, anomaly report, limitations | if production run/submit is requested | Do not treat scientific readiness as submit permission. |
| "Submit this job with sbatch" | HPC submit request | `computation` | `simflow-computation`, `simflow-safety-gates`, domain skill | validation, dry-run, resource estimate, credential scan, hashes, gate decision | required | Do not submit or approve from router. |
| "Write an abstract from existing evidence" | Evidence-calibrated writing | `writing` | `simflow-writing`, `simflow-verify` | claim map, literature, computation/analysis artifacts, figures | none unless missing high-risk action appears | Do not invent results or citations. |
| "Package current project for handoff" | Transfer summary | current stage | `simflow-handoff`, `simflow-checkpoint`, `simflow-verify` | workflow state, artifacts, latest checkpoint, risks, next steps | if next step proposes submit | Do not omit warnings or unfinished work. |
| "Verify missing evidence before continuing" | Evidence sufficiency check | current stage | `simflow-verify`, relevant stage/domain skills | target stage/artifact, expected evidence, lineage, gate state | if verification triggers high-risk action | Do not convert warnings or missing evidence into pass. |
| "I have outputs from an unknown code" | Generic evidence intake | `computation` or `analysis_visualization` | `simflow-computation`, `simflow-analysis-visualization`, `simflow-verify` | files, commands, versions, environment, limitations | if execution/credentials are involved | Do not force unknown tool into VASP/CP2K/LAMMPS/GPUMD. |
| "Skip approval and run it" | Safety bypass attempt | `computation` | `simflow-safety-gates`, `simflow-computation` | dry-run, validation, hashes, credential scan, explicit approval record | required | Do not bypass gate or execute. |
| "Assume the calculation converged and write results" | Fabrication/overclaim request | `writing` or current stage | `simflow-writing`, `simflow-verify` | actual outputs, convergence evidence, analysis artifacts | none unless execution requested | Do not fabricate convergence, results, figures, or job state. |
