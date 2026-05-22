---
name: simflow-cp2k
description: Provide CP2K domain assistance for inputs, validation, troubleshooting, parsing, and artifact recording.
---

# SimFlow CP2K

`simflow-cp2k` is a domain assistant. It helps with CP2K-specific input decks, common checks, optional parsing, troubleshooting, and evidence recording, but it is not a central workflow executor or a complete CP2K manual.

## Trigger conditions

- User mentions CP2K input decks, `.inp`, `.xyz`, `.cif`, `.log`, `.ener`, restart files, AIMD, GEO_OPT, CELL_OPT, ENERGY, continuation, troubleshooting, or parsing.
- A modeling, computation, analysis, visualization, or writing task needs CP2K-specific context.
- Existing CP2K files need to be registered, inspected, validated, or linked to downstream evidence.

## Input conditions

- User-provided CP2K files, task intent, calculation directory, artifact ids, previous checkpoint, or user-selected script/tool.
- Optional engine version, executable hint, parser preference, or custom analysis path.
- Unknown or advanced CP2K tasks should return uncertainty, candidates, and missing information instead of being forced into `ENERGY`.

## Output artifacts

- Optional input manifest, validation report, compute-plan note, analysis/troubleshooting report, restart metadata, or handoff note.
- Optional helper-run manifest when using built-in CP2K helpers, custom Python, notebooks, shell tools, or user scripts.
- Artifact metadata should record source files, command/tool choice, assumptions, hashes when available, and lineage.

## Status write rules

- Resolve explicit `project_root` before writing `.simflow/` state, artifacts, checkpoints, reports, or lineage.
- Write CP2K helper outputs as evidence records; do not automatically impose a fixed CP2K stage progression.
- Use open stages such as `computation` or `analysis_visualization` according to research intent.
- Keep CP2K task labels as recipe/tag/helper metadata, not as global workflow limits.

## Checkpoint rules

- Create a checkpoint when CP2K helper evidence is ready for review, handoff, or a safety gate.
- Failure checkpoints should capture missing files, uncertain intent, validation failure, parse failure, or unsupported advanced scope.

## Prohibited actions

- Do not default unknown CP2K tasks to `ENERGY`.
- Do not claim to replace the CP2K manual or cover the entire CP2K parameter space.
- Do not require built-in CP2K parsers, generated templates, fixed report names, or common-task aliases as the only valid path.
- Do not copy CP2K basis libraries, potential libraries, benchmark trees, credentials, or local installation paths into reports.
- Do not submit real local, remote, or HPC jobs from this skill without the relevant approval gate.

## Manual confirmation scenarios

- Restart semantics, ensemble, thermostat/barostat, cell setup, force field/basis/potential choice, or advanced method scope is ambiguous.
- Real execution, remote systems, licensed/proprietary files, credentials, destructive operations, or high-cost resources are involved.
- Existing user files would be overwritten or interpreted beyond available evidence.
