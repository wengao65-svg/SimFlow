---
name: simflow-computation
description: Use when a user asks to prepare, validate, dry-run, or submit computational simulation jobs.
---

# SimFlow Computation

## Purpose

`simflow-computation` is the computation-stage workflow contract for calculation
preparation, validation, dry-run evidence, submit-readiness handoff, and
user-provided computation evidence intake. It is not a central simulation
executor and does not replace domain skills or scheduler safety gates.

## Trigger Conditions

- The user asks to prepare inputs, validate a calculation setup, estimate
  resources, dry-run a job, record computation evidence, or submit a local,
  remote, or HPC job.
- The current research intent is computation, including input generation as an
  optional sub-activity.
- A planned or existing calculation needs evidence, approval, checkpointing, or
  handoff before it can be treated as ready for the next workflow stage.

## Computation Activities

- Input generation: create or register calculation input files without claiming
  real execution.
- Input validation: record file presence, non-empty checks, hashes, and
  lightweight consistency evidence.
- Dry-run planning: generate or register calculation manifests, job scripts,
  resource estimates, credential scans, and submit-readiness evidence. Prefer
  explicit or reusable user submit scripts over generating a new script.
- Generic evidence intake: record user-provided computation artifacts for
  tracked_only or unknown tools without forcing a helper route.
- Submit handoff: pass reviewed evidence and hashes to the safety gate and MCP
  connector path; do not submit directly from the skill contract.

## Support-Level Behavior

- `helper_supported`: built-in helpers may prepare or inspect bounded evidence,
  but dry-run evidence is still not a real calculation.
- `tracked_only`: record explicit user evidence and limitations; do not block
  planning only because a helper is unavailable.
- `unknown`: avoid software-specific claims; use generic evidence intake and
  label limitations clearly.

## Domain Skill Delegation

- VASP, CP2K, LAMMPS, GPUMD, and MLP domain skills own engine-specific file
  semantics, scientific checks, and troubleshooting guidance.
- `simflow-computation` owns orchestration-level evidence, submit-readiness,
  checkpointing, and gate handoff.
- Do not make a computation helper the only valid path for a domain task; a
  user-provided script, notebook, or external workflow is valid when evidence
  and limitations are recorded.

## Evidence Contract

- Calculation manifest with software, task, command, inputs, resources,
  environment, and intended outputs.
- Input files or input manifest with hashes and lineage.
- Input validation report.
- Dry-run report with script hash and input artifact hash.
- Resource estimate.
- Credential scan report.
- Job record only when a real job is approved and submitted.

## Submit-Readiness Handoff

- Preserve a `submit_readiness` payload containing project root, scheduler, job
  script path, dry-run evidence path, script hash, and input artifact hash.
- Preserve a `submit_request_template` payload for MCP submit fields:
  `project_root`, `script_path`, `scheduler`, `dry_run_evidence`,
  `script_hash`, `input_artifact_hash`, and `gate_decision_id`.
- Preserve user-provided submit scripts unchanged. If a task-specific
  adaptation is necessary, create a derived script under `.simflow/` with
  parent-script lineage; do not edit the original script in place.
- Treat project-local `scripts/submit/` as the default reusable submit-script
  library. Only reusable scripts belong there; one-off task scripts should stay
  in the calculation directory or be referenced explicitly.
- Set `real_submit_allowed` to `false` until an explicit `hpc_submit` gate
  decision id is recorded against matching evidence and hashes.
- If the job script or input hash changes after approval, require a new dry-run
  and approval.

## Status Semantics

- `planned`, `waiting`, `blocked`, `dry_run_complete`, `submitted`,
  `completed`, and `failed` are status labels for communicating evidence state;
  they are not a standalone runtime state machine defined by this skill.
- `waiting` means user-supplied inputs, potentials, existing files, or evidence
  are missing.
- `blocked` means validation, credential scan, hashes, approval, or gate
  conditions failed.
- `submitted` is valid only after a recorded gate-approved real submit.
- `completed` means stage evidence is complete; it must not imply scientific
  result completion unless output/job evidence supports it.
- `failed` work must produce failure evidence or a failure checkpoint.

## Status Write Rules

- Resolve `project_root` explicitly before writing `.simflow/` state,
  artifacts, reports, gates, jobs, or checkpoints.
- Register scripts, inputs, validation reports, dry-run evidence, credential
  scans, resource estimates, submit summaries, and job records as artifacts
  with metadata and lineage.
- Keep waiting, planned, dry-run-only, and tracked-only evidence labels visible
  in status, readiness, handoff, and writing inputs.
- Write canonical submit-readiness evidence under `.simflow/artifacts/compute/`
  and `.simflow/artifacts/security/`.
- Create a checkpoint after computation dry-run/readiness evidence is completed,
  and create or preserve failure evidence when validation, credential scan,
  approval, submission, or evidence registration fails.

## Safety Gate Handoff

- Real local, remote, or HPC execution must pass the same approval discipline.
- The gate must evaluate recorded evidence, not agent-provided booleans.
- Submit results must be recorded as job artifacts and `jobs.json` state only
  after a real approved submission.
- Do not record unfinished calculations as completed results.

## Prohibited Actions

- Do not submit real local, remote, or HPC jobs without passing the relevant
  approval gate.
- Do not skip dry-run, input validation, resource estimate, credential scan, or
  artifact hash recording when real execution is possible.
- Do not store credentials, expose licensed/proprietary files, or redistribute
  restricted simulation inputs.
- Do not require one specific simulation engine, scheduler, parser, plotting
  library, input builder, or helper script.

## Manual Confirmation Scenarios

- Real execution, remote access, licensed software, proprietary files, or
  destructive file operations are involved.
- Resource requests, wall time, queue, account, environment, or software
  version are uncertain.
- The job script or input hash differs from the evidence used for approval.
