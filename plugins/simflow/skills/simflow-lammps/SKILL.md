---
name: simflow-lammps
description: Provide LAMMPS-specific guidance for classical, reactive, and MLP-driven MD input review, execution diagnosis, restart, and output intake.
---

# LAMMPS Domain Skill

## Purpose

Act as the LAMMPS Domain Skill for one current Research Task Skill. It does not
own workflow progression, runtime approval, or persistent state.

## Use when

- The task involves LAMMPS input/data/restart files, pair styles, fixes,
  computes, thermo, dumps, packages, errors, or performance behavior.
- Classical MD, reactive MD, or MLP deployment uses LAMMPS.

## Do not use when

- The task is general MD methodology with no LAMMPS-specific question.
- The main issue is MLP dataset/training methodology rather than LAMMPS
  deployment; use `simflow-mlp` instead.

## Domain principles

- Identify units, atom style, boundary conditions, force field, type mapping,
  and intended ensemble before interpreting commands.
- Separate classical, reactive, and MLP deployment assumptions.
- Treat neighbor, communication, package, accelerator, and MPI choices as part
  of the execution environment, not the scientific model itself.
- Preserve restart semantics and avoid rebuilding a continued run from an
  inconsistent data file.
- Parse log/dump metadata before final property analysis; property methodology
  belongs to the analysis Task Skill.

## Minimum checks

- Included files, data files, potentials, and model files exist and match types.
- Units, timestep, masses, charges, atom style, boundaries, and pair coefficients
  are consistent.
- Ensemble fixes, thermostat/barostat damping, constraints, and run lengths are
  physically plausible.
- Required packages and pair styles are available in the target executable.
- Logs are checked for lost atoms, non-numeric values, dangerous builds, SHAKE
  failure, incomplete runs, drift, and restart completion.
- Dump columns, image flags, IDs, units, and frame cadence are known before
  trajectory analysis.

## Common failure modes

- Using the wrong unit system or type-to-element mapping.
- Treating a model file as sufficient evidence of correct MLP deployment.
- Ignoring missing image flags in diffusion or transport analysis.
- Continuing from an incompatible restart or changing timestep silently.
- Calling a run successful because the log file exists.

## Escalate uncertainty when

- Force-field provenance, type mapping, charge convention, or units are unclear.
- Required packages or MLP interfaces cannot be verified.
- Real execution, remote access, or a scientific parameter change is requested.

## Completion criteria

- LAMMPS-specific input and output semantics are understood.
- Execution warnings and scientific limitations are visible.
- Final property claims are deferred to appropriate analysis methodology.

## Optional references

- `references/lammps_official_sources.md`
- `references/lammps_input_validation.md`
- `references/lammps_force_fields_and_mlp.md`
- `references/lammps_md_workflows.md`
- `references/lammps_output_intake.md`
- `references/lammps_troubleshooting.md`
- `references/lammps_parameters.md`
- `references/lammps_tools.md`
