---
name: simflow-cp2k
description: Provide CP2K-specific guidance for input setup and review, Quickstep DFT basis and potential choices, MGRID/SCF convergence, optimization, AIMD, restart and continuation, troubleshooting, and output interpretation. Use when requests mention CP2K, GLOBAL/FORCE_EVAL/DFT/MGRID/SCF/QS/KIND/MOTION, ENERGY/GEO_OPT/CELL_OPT/MD, or CP2K input, restart, log, .ener, and trajectory files.
---

# CP2K Domain Skill

## Purpose

Provide CP2K-specific semantics to any current Research Task Skills that need
them, without owning workflow state, persistence, submission, or approval.

## Domain principles

- Infer the task from explicit intent and input sections. Do not default unknown
  CP2K tasks to `ENERGY`.
- Keep basis, potential, XC, cutoff, and SCF choices scientifically consistent.
- Preserve validated user input and local data-file conventions.
- Treat example inputs as starting points, not universal production settings.
- Distinguish a parsed output from a completed and scientifically adequate run.

## Minimum checks

- GLOBAL/RUN_TYPE matches the requested activity.
- FORCE_EVAL, DFT, MGRID, SCF, QS, XC, SUBSYS, CELL, COORD, and KIND sections
  are mutually consistent.
- Every element has an intentional basis and potential definition.
- Cutoff and REL_CUTOFF choices have appropriate convergence evidence.
- GEO_OPT, CELL_OPT, or MD settings match the requested ensemble and timescale.
- Restart files exist, are compatible, and do not silently change the method.
- Logs are checked for aborts, SCF failures, warnings, drift, and normal end.

## Common failure modes

- Missing basis/potential data or mismatched KIND labels.
- Treating a portable example as a converged production input.
- Hiding SCF non-convergence behind a normal-looking trajectory.
- Restarting with incompatible cell, coordinates, basis, or method settings.
- Interpreting a short AIMD run as statistically converged.

## Escalate uncertainty when

- The intended RUN_TYPE, electronic method, periodicity, basis family, or
  potential family is unclear.
- Real execution, remote access, credentials, or expensive resources are needed.
- A convergence workaround would change scientific parameters.

## Completion criteria

- CP2K inputs and outputs are consistent with the explicit scientific task.
- Convergence and restart limitations are reported.
- No completion or scientific claim exceeds the available output evidence.

## Optional references

Load only the references needed for the concrete CP2K request. Use official
sources for exact keyword semantics, example patterns for portable setup, and
task checklists for review; do not load the local source-tree index unless the
user actually provides such a tree.

- `references/cp2k_official_sources.md`: Read first when checking exact
  keywords, defaults, units, version-sensitive behavior, or official workflow
  claims.
- `references/cp2k_example_patterns.md`: Read when preparing or reviewing
  portable calculation directories for ENERGY, cutoff convergence, GEO_OPT,
  CELL_OPT, AIMD, restart, or output review.
- `references/cp2k_task_checklists.md`: Read after identifying the RUN_TYPE when
  performing a structured ENERGY, GEO_OPT, CELL_OPT, AIMD, restart, parsing, or
  advanced-workflow review.
- `references/cp2k_parameters.md`: Read when reviewing `GLOBAL`, `FORCE_EVAL`,
  `DFT`, `QS`, `MGRID`, `SCF`, `XC`, `SUBSYS`, `KIND`, `MOTION`, or restart
  parameter consistency.
- `references/cp2k_troubleshooting.md`: Read for failed runs, SCF or grid
  convergence, MD drift, optimization problems, missing basis/potential files,
  restart failures, or suspicious output.
- `references/cp2k_local_examples_index.md`: Read only when the user provides a
  CP2K source tree or `CP2K_SOURCE_DIR`/`CP2K_ROOT`; use it to locate docs,
  tests, benchmarks, and data without copying them as production templates.
- `references/cp2k_methods_index.md`: Read only for a quick view of common
  helper coverage and which advanced method families require broader official
  guidance; do not treat it as a scientific authority.
- `references/cp2k_common_workflows.md`: Read for a concise summary of common
  ENERGY, GEO_OPT, CELL_OPT, AIMD, restart, and parsing motifs; use the example
  patterns and checklists for detailed preparation or review.
- `references/cp2k_tools.md`: Read when considering ASE's CP2K interface, CP2K
  bundled utilities, or custom parsing and notebook routes.
