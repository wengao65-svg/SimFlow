---
name: simflow-vasp
description: Handle VASP-specific setup, validation, tool orchestration, parsing, and troubleshooting in SimFlow.
---

# SimFlow VASP Skill

## Role

`simflow-vasp` is a VASP workflow orchestration layer for common tasks. It is not a VASP parameter encyclopedia, not a VASPKIT replacement, and not a py4vasp replacement.

Use it to classify the user request, identify missing inputs and predecessor calculations, choose available local tools, generate SimFlow reports, register artifacts, and create checkpoints.

## Covered Tasks

- Relaxation: `relax`
- Static SCF: `static`, `scf`
- Density of states: `dos`
- Band structure: `band`, `bands`
- AIMD: `aimd`, `md`
- Basic NEB setup checks: `neb`, `neb_basic`
- Input checks for surface, adsorption, and defect models
- Output parsing and convergence checks
- Troubleshooting for common VASP errors, warnings, and workflow questions

## Tool Policy

- Prefer existing SimFlow runtime, templates, validators, parsers, artifact registry, state, and checkpoint helpers.
- Detect local VASPKIT with `runtime.lib.vasp_tools`; use it only as an optional helper for common pre/post-processing plans.
- Prefer `py4vasp` when `vaspout.h5` exists and `py4vasp` imports successfully.
- Fall back to SimFlow parsers for `vasprun.xml`, `OUTCAR`, `OSZICAR`, and `EIGENVAL` when py4vasp is unavailable or fails.
- When parameter semantics, workflow steps, or version behavior are uncertain, use official VASP Wiki and py4vasp documentation through `runtime.lib.vasp_lookup`; do not invent answers from memory.

## Required Outputs

For common task orchestration, produce and register:

- `reports/vasp/input_manifest.json`
- `reports/vasp/validation_report.json`
- `reports/vasp/compute_plan.json`
- `reports/vasp/analysis_report.json`
- `reports/vasp/handoff_artifact.json`

Each run must update SimFlow state and create a stage checkpoint.

## Validation Focus

- POSCAR/POTCAR element order consistency using metadata only.
- KPOINTS mode compatibility with task type, especially mesh vs line-mode.
- DOS and band workflows require predecessor static SCF output, especially `CHGCAR`.
- AIMD inputs must use MD-style ionic settings such as `IBRION=0` and `NSW>0`.
- NEB basic checks must confirm image-directory structure.
- Surface, adsorption, and defect tasks should report structural risks rather than silently accepting incomplete inputs.
- Real HPC submission must remain blocked unless the existing `hpc_submit` approval gate passes.

## Prohibited Actions

- Do not generate, copy, distribute, snapshot, or print POTCAR content.
- Do not assume the user owns a VASP license.
- Do not submit real HPC jobs from this skill.
- Do not bypass verification gates or checkpoint rules.
- Do not expand this skill into a complete INCAR tag database.
- Do not modify the Codex plugin adapter layer.

## Scripts

- `scripts/generate_vasp_inputs.py`: generate common-task INCAR/KPOINTS/POSCAR and POTCAR metadata instructions.
- `scripts/orchestrate_vasp_task.py`: classify and orchestrate common VASP tasks, write reports, register artifacts, and checkpoint.
- `scripts/validate_vasp_outputs.py`: validate output convergence with fallback parser support.
- `scripts/troubleshoot_vasp.py`: produce source-backed troubleshooting summaries from official docs.
- `scripts/plot_band_structure.py`: plot parsed band data when available.

## Handoff

At session end or handoff, report current workflow state, produced VASP artifacts, latest checkpoint, validation risks, and whether approval is needed before any real compute submission.
