# LAMMPS Troubleshooting

Troubleshooting should capture the minimal failing input, environment evidence,
and the smallest changed variable that explains the behavior.

## Common Failure Classes

- Missing package or unknown pair/fix/compute style: compare input to `lmp -h`
  output and official package docs.
- Lost atoms, NaN pressure/energy, or exploding temperature: review timestep,
  overlaps, units, potential/type mapping, neighbor settings, and boundaries.
- Dangerous builds or poor neighbor behavior: record neighbor skin, delay/every,
  cutoff, density, and timestep.
- ReaxFF/COMB instability: review charge equilibration, timestep, parameters,
  and species coverage.
- GPU/KOKKOS/OPENMP mismatch: record executable, suffix/package settings,
  MPI launcher, thread counts, and device count.
- MLP runtime errors: check model path, model format, species/type mapping,
  installed plugin/package, Python environment when applicable, and cutoff/domain limits.

## Minimum Diagnostic Bundle

- top-level input and included files.
- data/restart source and hashes when allowed.
- relevant potential/model metadata.
- exact command line or scheduler script if execution was approved.
- LAMMPS version, `lmp -h` output, package list, accelerator settings.
- last 100-200 log lines and the first error/warning line.

Do not "fix" by silently changing physics. Any timestep, ensemble, force-field,
charge, type mapping, or boundary change must be recorded as a scientific decision.
