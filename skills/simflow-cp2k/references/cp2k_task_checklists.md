# CP2K Task Checklists

Use these checklists as conservative prompts for inspection. They are not a substitute for the CP2K manual.

## ENERGY / static DFT

- Confirm `GLOBAL/RUN_TYPE ENERGY`.
- Confirm one or more `FORCE_EVAL` sections, normally `METHOD QS` for Quickstep DFT.
- Confirm `DFT/BASIS_SET_FILE_NAME`, `DFT/POTENTIAL_FILE_NAME`, `QS`, `MGRID`, `SCF`, and `XC`.
- Confirm `SUBSYS/CELL`, `SUBSYS/TOPOLOGY` or inline `COORD`, coordinate format, and `KIND` blocks for all elements.
- Check charge, multiplicity, periodicity, cell size/vacuum, and whether k-points are needed.
- Check `CUTOFF` and `REL_CUTOFF` are justified by convergence evidence or a stated accuracy target.
- Report missing force/stress needs explicitly; `ENERGY` is not a relaxation or MD run.

## GEO_OPT

- Confirm `GLOBAL/RUN_TYPE GEO_OPT` and `MOTION/GEO_OPT`.
- Confirm the DFT setup is already suitable for single-point energy/force evaluation.
- Check `GEO_OPT/TYPE`, `OPTIMIZER`, `MAX_ITER`, `MAX_FORCE`, `RMS_FORCE`, `MAX_DR`, and `RMS_DR`.
- Check constraints, fixed atoms, molecular drift handling, and whether the cell must remain fixed.
- Check that output trajectory and restart printing are sufficient for handoff.
- Treat an optimization as complete only when the CP2K output shows the required criteria have been satisfied. Do not infer completion from the presence of a restart file alone.

## CELL_OPT

- Confirm `GLOBAL/RUN_TYPE CELL_OPT` and `MOTION/CELL_OPT`.
- Check `CELL_OPT/TYPE`, optimizer, pressure target, `KEEP_SYMMETRY`, and whether the chosen cell degrees of freedom match the physics.
- Check periodicity, stress relevance, cutoff convergence, and basis/grid sensitivity. Cell optimization can be more sensitive to Pulay-like numerical effects than a fixed-cell static calculation.
- Record whether external pressure units and target pressure are explicit.
- Report when the requested task is really equation-of-state sampling rather than a single cell optimization.

## AIMD / MD

- Confirm `GLOBAL/RUN_TYPE MD` and `MOTION/MD`.
- Check ensemble, timestep, number of steps, target temperature, thermostat, barostat, pressure, constraints, and initialization/restart semantics.
- For CP2K DFT-MD, check `QS/EXTRAPOLATION`, `EXTRAPOLATION_ORDER`, `EPS_SCF`, `EPS_DEFAULT`, `MGRID/CUTOFF`, and `REL_CUTOFF`.
- Check output cadence for `.ener`, trajectory, velocity, force, and restart files.
- Inspect `.ener` for equilibration, temperature, potential energy, conserved quantity, and CPU-time trends.
- For NVE evidence, check energy oscillation and drift. If drift matters, advise tightening SCF/grid tolerances or reducing timestep before claiming production-quality dynamics.
- Separate equilibration and production windows before computing statistical properties.

## Restart / continuation

- Confirm a compatible restart artifact exists and is referenced by `EXT_RESTART/RESTART_FILE_NAME`, `SCF_GUESS RESTART`, or a CP2K-generated restart input.
- Check project-name continuity, step counters, coordinates, velocities for MD, thermostat/barostat state where relevant, and whether restart counters should be reset.
- Preserve restart files. Never overwrite a user restart without explicit approval.
- Treat restart semantics as ambiguous when the user only provides a file name without explaining whether this is SCF, geometry, MD, or workflow continuation.

## Parse / troubleshoot

- Inventory logs, `.ener`, trajectories, restart files, generated structures, and the original input deck.
- Extract CP2K version, run type, project name, normal end/abort, final energy, warning count, SCF evidence, MD steps, final temperature, conserved quantity, and restart metadata when available.
- Do not call a calculation converged only because the parser found a final energy. Check normal end, convergence messages, warnings/errors, and task-specific criteria.
- For partial outputs, report what can be supported and what remains unknown.

## Advanced or custom workflows

For NEB, metadynamics, path integrals, QMMM, DFTB, xTB, hybrid functionals, GW/RPA/MP2, ML potentials, spectroscopy, or property workflows:

- Return candidates and missing information instead of forcing the task into a common alias.
- Load `references/cp2k_official_sources.md` and inspect matching local CP2K docs/tests/benchmarks.
- Ask for method intent, predecessor files, convergence standards, and whether the goal is input preparation, dry-run review, output parsing, or scientific interpretation.
- Use helper scripts only for the parts they actually support. For unsupported sections, do static inspection and source-backed guidance.
