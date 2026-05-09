---
name: simflow-cp2k
description: Handle CP2K common-task orchestration, validation, parsing, checkpoints, and handoff inside SimFlow.
---

# SimFlow CP2K

`simflow-cp2k` is the SimFlow CP2K workflow orchestration layer.

It covers common CP2K tasks only:
- `ENERGY` / single point
- `GEO_OPT`
- basic `CELL_OPT`
- basic `AIMD` in `NVT`, `NVE`, and `NPT`
- restart / continuation checks
- input validation
- output parsing
- convergence / troubleshooting
- artifact, checkpoint, and handoff reporting

It does not cover the full CP2K parameter space and it does not replace the CP2K manual or official documentation.

## Trigger conditions

- User asks to prepare, validate, inspect, continue, or troubleshoot a CP2K job.
- User provides a CP2K input deck, structure, restart file, log, energy file, or trajectory for common-task handling.
- A SimFlow stage needs CP2K dry-run planning, parsing, artifact registration, or handoff packaging.

## Input conditions

- `project_root` must be provided explicitly or resolved from the user project directory.
- All reports, artifacts, checkpoints, and workflow state must be written relative to `project_root`.
- Before writing any workflow state, ensure or initialize `.simflow/` under `project_root`.
- Supported structure/input sources are common lightweight inputs such as `.inp`, `.xyz`, `.cif`, `.log`, `.ener`, `*-pos-1.xyz`, and `.restart`.
- Real HPC execution is out of scope for this skill unless a later approval gate is passed.

## Execution Flow

1. Resolve `project_root` explicitly and reject plugin-root or cache-root writes.
2. Ensure or initialize `.simflow/` under `project_root`.
3. Classify the CP2K task and identify required or missing inputs.
4. Generate or normalize common-task CP2K inputs when requested.
5. Validate the CP2K input deck and referenced coordinate or restart files.
6. Build a dry-run compute plan only. Do not submit.
7. Parse available CP2K outputs when present.
8. Write reports under `project_root/reports/cp2k/`.
9. Register artifacts, create a checkpoint, update SimFlow stage state, and write a handoff artifact.

## Output artifacts

- `reports/cp2k/input_manifest.json`
- `reports/cp2k/validation_report.json`
- `reports/cp2k/compute_plan.json`
- `reports/cp2k/analysis_report.json`
- `reports/cp2k/handoff_artifact.json`

Additional task-local artifacts may include generated `.inp`, normalized `.xyz`, or parsed restart metadata, but the report set above is the standard orchestration output.

## Status write rules

- Always write reports, artifacts, checkpoints, and workflow state relative to `project_root`.
- Always ensure `.simflow/` under `project_root` before writing workflow state.
- Never infer the user project from MCP server cwd, plugin root, or Codex cache.
- Report JSON must be written under `project_root/reports/cp2k/` and re-read after write validation.
- Artifact, checkpoint, and state updates must use SimFlow runtime helpers with explicit `project_root`.

## Checkpoint rules

- Create a checkpoint after a successful orchestration pass.
- On failure, create a failure checkpoint and record the failure in the stage state and reports.
- The checkpoint must include workflow association, stage association, and current artifact/state snapshot.

## Prohibited actions

- Do not present this skill as a full CP2K parameter encyclopedia.
- Do not claim to replace the CP2K official manual.
- Do not submit real HPC jobs from this skill by default.
- Do not depend on MCP cwd, plugin root, Codex cache, or developer-local CP2K source trees as `project_root`.
- Do not copy CP2K basis libraries, potential libraries, benchmark trees, or local installation paths into reports or generated defaults.

## Manual confirmation scenarios

- Any real HPC submission requires an approval gate.
- Ambiguous restart / continuation intent that would change run semantics should be confirmed.
- Unsupported advanced CP2K methods or parameter spaces outside the common-task layer should be escalated to manual review instead of guessed.
