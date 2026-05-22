---
name: simflow-vasp
description: Provide VASP domain assistance for inputs, validation, troubleshooting, parsing, and artifact recording.
---

# SimFlow VASP

`simflow-vasp` is a domain assistant. It can suggest checks, templates, documentation entry points, and optional helper scripts for VASP work, but it is not the workflow contract and does not define the limit of valid VASP tasks.

## Trigger conditions

- User mentions VASP, INCAR, POSCAR, POTCAR metadata, KPOINTS, OUTCAR, OSZICAR, vasprun.xml, CHGCAR, DOSCAR, EIGENVAL, NEB, phonons, AIMD, SOC, hybrid functionals, DFT+U, defects, surfaces, or adsorption.
- A computation, modeling, analysis, visualization, troubleshooting, or writing task needs VASP-specific context.
- User asks to inspect or prepare VASP-related artifacts without real job submission.

## Input conditions

- Natural-language VASP intent, local files, artifact ids, calculation directory, or previous checkpoint.
- Optional user-selected task type, software version, script, parser, template, or external tool.
- Unknown or unlisted tasks should return candidates and missing information, not a forced alias.

## Output artifacts

- Optional input manifest, validation report, compute-plan note, analysis/troubleshooting report, or handoff note.
- Optional helper-run manifest when using SimFlow parsers, py4vasp, VASPKIT, custom Python, shell commands, or user scripts.
- Artifact metadata should record source files, command/tool choice, task uncertainty, hashes when available, and lineage.

## Status write rules

- Resolve explicit `project_root` before writing `.simflow/` state, artifacts, checkpoints, reports, or lineage.
- Write reports only as evidence records; do not advance a fixed VASP workflow automatically.
- Use open stages such as `modeling`, `computation`, or `analysis_visualization` according to research intent.
- Keep recipe/tag values such as `dft`, `aimd`, `neb`, `phonon`, `defect`, or `custom` separate from workflow stage.

## Checkpoint rules

- Create a checkpoint when a VASP helper result is ready for review, handoff, or a safety gate.
- Failure checkpoints should capture missing files, uncertain task intent, validation failure, or unavailable licensed/proprietary resources.

## Prohibited actions

- Do not default unknown VASP tasks to `static`.
- Do not treat common aliases as the full VASP capability surface.
- Do not require py4vasp, VASPKIT, SimFlow parsers, fixed report names, or generated templates as the only valid path.
- Do not generate, copy, distribute, snapshot, or print POTCAR content.
- Do not submit real local, remote, or HPC jobs from this skill without the relevant approval gate.

## Manual confirmation scenarios

- Task intent, predecessors, charge/spin/SOC/DFT+U/hybrid/phonon/NEB setup, or validation standard is ambiguous.
- Real execution, licensed files, proprietary files, credentials, remote systems, or high-cost resources are involved.
- Existing user inputs would be overwritten or interpreted in a way that changes scientific meaning.
