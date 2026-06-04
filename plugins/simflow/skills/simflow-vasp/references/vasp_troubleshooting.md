# VASP Troubleshooting Reference

Use this reference when a VASP task fails, converges poorly, produces suspicious output, or needs an error/warning summary. Verify issue-specific behavior against official VASP documentation before changing scientific parameters.

## First-pass triage

- Identify which stage failed: input parsing, electronic minimization, ionic relaxation, MD stability, post-processing, filesystem/runtime, or scheduler/resource issue.
- Preserve original inputs and outputs. Do not overwrite evidence while troubleshooting.
- Check `OUTCAR`, `OSZICAR`, `vasprun.xml`, `vaspout.h5`, stdout/stderr, and scheduler logs when available.
- Record VASP version, executable, MPI/OpenMP settings, node/core layout, memory, and walltime when relevant.
- Distinguish "job stopped" from "calculation converged"; scheduler success is not scientific convergence.

## Input consistency issues

- `POSCAR`/`POTCAR` mismatch: verify species order and atom counts; do not expose POTCAR content.
- `KPOINTS` mismatch: line-mode paths are usually for band structures; mesh k-points are usually for SCF/relax/DOS.
- Restart mismatch: ensure `WAVECAR`, `CHGCAR`, `CONTCAR`, spin/SOC settings, and pseudopotential choices are compatible with the new task.
- Selective dynamics or constraints: inspect whether frozen atoms/layers match the scientific model.

## Electronic convergence

- Evidence to inspect: number of electronic steps, final residuals, energy oscillation, `NELM` exhaustion, warnings, and charge/magnetization behavior.
- Common review levers: `ALGO`, `NELM`, `EDIFF`, `ISMEAR/SIGMA`, mixing tags, initial magnetic moments, k-point density, and structure quality.
- For metals, smearing choices and partial occupancies matter; for insulators/semiconductors, tetrahedron or small smearing may be more appropriate depending on the task.
- Do not automatically loosen convergence thresholds without recording why the change is scientifically acceptable.

## Ionic relaxation and force issues

- Evidence to inspect: max force, stress tensor, `EDIFFG`, ionic step count, `NSW`, `IBRION`, `POTIM`, `ISIF`, and final geometry.
- If forces do not decrease, inspect structure reasonableness, constraints, initial distances, cell shape, and whether the chosen relaxation mode is appropriate.
- If relaxation stops at `NSW`, record as not fully converged unless force/stress evidence supports completion.

## MD instability

- Evidence to inspect: temperature drift, total-energy drift, pressure/volume behavior, close contacts, timestep, thermostat/barostat parameters, and restart continuity.
- Review timestep and ensemble choices before interpreting diffusion, RDF, viscosity, or phase-transition claims.
- Separate equilibration from production; do not analyze transient startup as production evidence without explicit rationale.

## NEB and transition-state issues

- Verify image order, atom order, endpoint consistency, spring/climbing settings, and whether images crossed or collapsed.
- Inspect per-image convergence, forces along the path, and the highest-energy image.
- Do not claim a barrier from an unconverged or misordered image set.

## Magnetism, DFT+U, SOC, and hybrid issues

- Magnetism: try distinct initial magnetic states only with recorded rationale; final moment alone may not prove global magnetic order.
- DFT+U: record U/J provenance and avoid comparing different U choices as if they were the same Hamiltonian.
- SOC/noncollinear: verify executable, tags, symmetry, axis, predecessor workflow, and interpretation of spin/orbital moments.
- Hybrid/GW/BSE/RPA: expect stronger resource and convergence requirements; check NBANDS, cutoffs, k meshes, frequency/grid choices, and predecessor orbitals/densities.

## Parse and analysis failures

- Prefer py4vasp for `vaspout.h5` when available; fallback parsers may be partial.
- If parsing `EIGENVAL`, record Fermi-level source because EIGENVAL alone may not carry all context needed for publication-grade plots.
- If parsing XML/HDF5 fails, report parser/tool version and file completeness instead of forcing a result.
- For figures, record the exact parser/tool and script used, and keep raw data separate from rendered plots.

## Failure reporting

Failure reports should include:

- request/task classification and confidence
- available and missing inputs
- official source URLs checked or queued for verification
- failure category and exact evidence file(s)
- conservative diagnosis and alternative hypotheses
- recommended next checks
- whether user approval is needed before real execution or costly reruns
- checkpoint id when a failure checkpoint is created
