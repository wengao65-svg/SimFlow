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

## Input Conditions

- Accept user-provided input files, generated input files, model artifacts,
  calculation manifests, previous checkpoints, or explicit calculation plans.
- Accept optional software, scheduler, resource, environment, license, account,
  queue, walltime, module, and command information.
- Require explicit approval evidence before any real local, remote, or HPC
  execution.

## Computation Sub-Activities

- Input generation: create or register calculation input files without claiming
  real execution.
- Input validation: check required files, empty files, hashes, and lightweight
  consistency evidence.
- Dry-run planning: generate calculation manifests, job scripts, resource
  estimates, credential scans, and submit-readiness evidence.
- Generic evidence intake: register user-provided computation artifacts for
  tracked-only or unknown tools.
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

## State Machine

- `planned`: calculation intent or input plan exists.
- `dry_run_complete`: submit-readiness evidence exists; real submit remains
  disallowed.
- `waiting`: required user inputs, potentials, existing files, or evidence are
  missing.
- `blocked`: validation, credential scan, hashes, approval, or gate conditions
  failed.
- `submitted`: only valid after a recorded gate-approved real submit.
- `completed`: stage evidence is complete; do not imply scientific result
  completion unless output/job evidence supports it.
- `failed`: helper, validation, approval, submission, or evidence registration
  failed and must produce failure evidence or a failure checkpoint.

## Required Evidence

- Calculation manifest with software, task, command, inputs, resources,
  environment, and intended outputs.
- Input files or input manifest with hashes and lineage.
- Input validation report.
- Dry-run report with script hash and input artifact hash.
- Resource estimate.
- Credential scan report.
- Job record only when a real job is approved and submitted.

## Submit-Readiness Contract

- Preserve a `submit_readiness` payload containing project root, scheduler,
  job script path, dry-run evidence path, script hash, and input artifact hash.
- Preserve a `submit_request_template` payload that maps directly to MCP submit fields:
  `project_root`, `script_path`, `scheduler`, `dry_run_evidence`,
  `script_hash`, `input_artifact_hash`, and `gate_decision_id`.
- Set `real_submit_allowed` to `false` until an explicit `hpc_submit` gate
  decision id is recorded against matching evidence and hashes.

## Safety Gate Handoff

- Real local, remote, or HPC execution must pass the same approval discipline.
- The gate must evaluate recorded evidence, not agent-provided booleans.
- If the job script or input hash changes after approval, require a new dry-run
  and approval.
- Submit results must be recorded as job artifacts and `jobs.json` state only
  after a real approved submission.

## Status Write Rules

- Resolve `project_root` explicitly before writing `.simflow/` state,
  artifacts, reports, gates, jobs, or checkpoints.
- Register scripts, inputs, validation reports, dry-run evidence, credential
  scans, resource estimates, submit summaries, and job records as artifacts
  with metadata and lineage.
- Keep waiting, planned, dry-run-only, and tracked-only evidence labels visible
  in status, readiness, handoff, and writing inputs.

## Artifact / Checkpoint Rules

- Write canonical submit-readiness evidence under `.simflow/artifacts/compute/`
  and `.simflow/artifacts/security/`.
- Create a checkpoint after computation dry-run/readiness evidence is completed.
- Create or preserve failure evidence when validation, credential scan,
  approval, submission, or evidence registration fails.
- Do not record unfinished calculations as completed results.

## Failure / Waiting Semantics

- Return `waiting` when missing information can be supplied by the user, such
  as force-field provenance, potential files, calculation inputs, or tracked-only
  evidence.
- Return `blocked` when recorded evidence fails a gate, validation, hash, or
  credential condition.
- Return explicit capability warnings for unsupported helper routes without
  treating unknown software as forbidden.

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

## Examples

- Preparing VASP inputs through the VASP domain skill and recording computation
  dry-run evidence remains dry-run-only until `hpc_submit` is approved.
- Recording existing LAMMPS inputs through direct computation entry is valid
  when input files, hashes, resource estimates, credential scan, and limitations
  are preserved.
- Unknown software can proceed through generic computation evidence intake, but
  SimFlow must label it as tracked-only or unknown rather than helper-supported.
