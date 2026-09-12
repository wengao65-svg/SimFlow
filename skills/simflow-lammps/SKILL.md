---
name: simflow-lammps
description: Provide LAMMPS-specific guidance for input/data/restart review, classical and reactive force fields, MLP deployment, ensembles and timesteps, packages and accelerators, runtime diagnosis, and log/dump intake. Use when requests mention LAMMPS, pair_style/pair_coeff, fixes/computes/thermo, log.lammps, dump trajectories, lost atoms, dangerous builds, ReaxFF, EAM/MEAM, KIM, or MLP pair styles. Combine with simflow-mlp for dataset, training, transferability, or production-readiness questions.
---

# LAMMPS Domain Skill

## Purpose

Provide LAMMPS-specific semantics to any current Research Task Skills that need
them. It does not own workflow progression, runtime approval, or persistent
state.

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
- Combine with `simflow-mlp` when LAMMPS deployment also depends on dataset,
  validation, transferability, or production-readiness methodology.

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

Select references according to whether the request concerns syntax, static
validation, force-field deployment, MD workflow design, output intake, or
failure diagnosis. Final property-analysis methodology remains with the
analysis Task Skill.

- `references/lammps_official_sources.md`: Read when verifying command syntax,
  package availability, accelerator behavior, pair/fix/compute semantics,
  restart behavior, or official error meanings.
- `references/lammps_input_validation.md`: Read when statically reviewing an
  input script, data file, restart source, includes, thermo setup, or dump
  configuration.
- `references/lammps_force_fields_and_mlp.md`: Read when reviewing classical or
  reactive potentials, KIM models, charge models, type mapping, potential
  provenance, or MLP deployment in LAMMPS.
- `references/lammps_md_workflows.md`: Read for minimization, equilibration,
  production, rerun, deformation, shock, transport, restart planning, or
  smoke-versus-production distinctions.
- `references/lammps_output_intake.md`: Read when ingesting log, dump, data, or
  restart outputs before downstream RDF, MSD, diffusion, transport, mechanical,
  or visualization analysis.
- `references/lammps_troubleshooting.md`: Read for missing packages, unknown
  styles, lost atoms, NaN values, dangerous builds, ReaxFF instability,
  accelerator mismatches, or MLP runtime errors.
- `references/lammps_parameters.md`: Read as a compact first-pass evidence and
  reference index when the request is broad; skip it when a more specific
  reference has already been selected.
- `references/lammps_tools.md`: Read when considering the LAMMPS Python
  interface, bundled utilities, Pizza.py, or another LAMMPS-specific tool route.
