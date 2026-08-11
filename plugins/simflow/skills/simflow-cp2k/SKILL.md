---
name: simflow-cp2k
description: Provide CP2K-specific guidance for inputs, basis and potential choices, convergence, restart, AIMD, troubleshooting, and output interpretation.
---

# CP2K Domain Skill

## Purpose

Act as the CP2K Domain Skill for the current Research Task Skill without owning
workflow state, persistence, submission, or approval.

## Use when

- The task involves CP2K input, GLOBAL, FORCE_EVAL, DFT, MGRID, SCF, QS, KIND,
  MOTION, ENERGY, GEO_OPT, CELL_OPT, AIMD, restart files, logs, `.ener`, or
  trajectories.
- CP2K-specific convergence, basis, potential, cutoff, or restart semantics are
  needed.

## Do not use when

- The request is engine-independent or another Domain Skill owns the software.

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

- `references/cp2k_official_sources.md`
- `references/cp2k_example_patterns.md`
- `references/cp2k_task_checklists.md`
- `references/cp2k_parameters.md`
- `references/cp2k_troubleshooting.md`
- `references/cp2k_local_examples_index.md`
- `references/cp2k_methods_index.md`
- `references/cp2k_common_workflows.md`
- `references/cp2k_tools.md`
