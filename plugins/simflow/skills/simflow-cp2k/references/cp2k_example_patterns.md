# CP2K Example Patterns

Use this reference as the default portable CP2K example layer. It is designed for preparing calculation directories that may run in a separate execution environment. Do not assume the current workspace has CP2K, MPI, modules, or the same basis/potential library paths as the execution target.

## Calculation-directory model

A CP2K calculation directory prepared for handoff usually contains:

- One CP2K input deck, for example `energy.inp`, `geo_opt.inp`, `cell_opt.inp`, or `md.inp`.
- Coordinate input, for example `structure.xyz`, `structure.cif`, or inline `&COORD`.
- Optional restart input or restart file when continuing a prior calculation.
- Optional project-local basis, potential, topology, or force-field files only when the target CP2K environment will not provide them.
- A dry-run compute plan or job-script draft that records the intended executable, input file, output file, modules/environment, resources, and transfer assumptions.
- A manifest listing files to upload and expected files to retrieve.

Do not bake local absolute paths into CP2K input decks unless the user confirms those paths exist in the target execution environment. Prefer relative paths inside the calculation directory or CP2K library names that are valid on the target CP2K installation.

## Static DFT / ENERGY pattern

Use for a fixed-geometry energy and electronic-structure check.

Minimum conceptual sections:

- `GLOBAL`: `PROJECT`, `RUN_TYPE ENERGY`, and a suitable `PRINT_LEVEL`.
- `FORCE_EVAL`: usually `METHOD QS` for Quickstep DFT.
- `FORCE_EVAL/DFT`: basis and potential file names, charge, multiplicity, `QS`, `MGRID`, `SCF`, and `XC`.
- `FORCE_EVAL/SUBSYS`: cell, coordinates or topology, and `KIND` blocks for every element or kind label.

Evidence to record:

- Structure source, element counts, cell/periodicity, charge/multiplicity, basis/potential names, functional, cutoff settings, SCF settings, and whether the input is meant only for static energy or also for forces/stress.
- Whether cutoff and SCF convergence are already established or still missing.

## CUTOFF and REL_CUTOFF convergence pattern

Use when the user asks for reliable DFT input preparation or when forces/stress/MD quality matters.

Workflow:

1. Start from a working static `ENERGY` input for the actual system or a representative cell.
2. Choose a high enough `REL_CUTOFF` while sweeping `CUTOFF` across a reasonable range for the basis/potential family.
3. Inspect total-energy stability first, then repeat or refine for `REL_CUTOFF`.
4. For geometry optimization, cell optimization, phonons, and MD, check force or stress sensitivity, not only total energy.
5. Record the convergence criterion, tested values, property monitored, final chosen values, and whether the result is preliminary.

Important interpretation:

- `CUTOFF` controls the finest real-space grid in the multigrid representation.
- `REL_CUTOFF` controls how Gaussian products are assigned across grid levels.
- Low `REL_CUTOFF` can make a high `CUTOFF` ineffective for some basis functions.

## GEO_OPT pattern

Use for fixed-cell relaxation of atomic positions.

Required intent checks:

- `GLOBAL/RUN_TYPE GEO_OPT`.
- `MOTION/GEO_OPT` with optimizer, `MAX_ITER`, and convergence thresholds such as maximum/RMS force and displacement.
- DFT settings that are accurate enough for forces, not only total energy.
- Constraints, fixed atoms, molecular drift concerns, and whether the cell should remain fixed.

Completion evidence:

- Do not treat the presence of a restart or final coordinate file as proof of convergence.
- Inspect CP2K output for the task-specific geometry criteria and normal termination.
- Record final structure lineage and whether any constraints were active.

## CELL_OPT pattern

Use for coupled relaxation of cell and atomic positions.

Required intent checks:

- `GLOBAL/RUN_TYPE CELL_OPT`.
- `MOTION/CELL_OPT` with optimizer, pressure target, cell degrees of freedom, symmetry handling, and pressure units.
- Stress-quality DFT settings and grid/basis convergence evidence.
- Whether the user actually needs a single cell optimization or an equation-of-state scan.

Risk notes:

- Cell optimization can be more sensitive to numerical grid and basis choices than a fixed-cell static calculation.
- Record pressure convention and whether external pressure is physically intended.

## AIMD / MD pattern

Use for ab initio molecular dynamics setup, continuation, or output review.

Input checks:

- `GLOBAL/RUN_TYPE MD` and `MOTION/MD`.
- Ensemble, timestep, steps, target temperature, thermostat, barostat, constraints, restart semantics, and output frequencies.
- `QS/EXTRAPOLATION` and `EXTRAPOLATION_ORDER`, because density/wavefunction guesses change the MD stability and cost.
- `EPS_SCF`, `QS/EPS_DEFAULT`, `MGRID/CUTOFF`, and `MGRID/REL_CUTOFF` for force quality.

Output checks:

- CP2K commonly writes trajectory files such as `PROJECT-pos-1.xyz` and energy files such as `PROJECT-1.ener`.
- The `.ener` file should be inspected for step, time, kinetic energy, temperature, potential energy, conserved quantity, and CPU-time trends.
- Separate equilibration and production windows before computing averages or transport properties.
- For NVE quality checks, inspect short-time oscillation and long-time drift of the conserved quantity.

Risk notes:

- Thermostats can mask force-quality problems. Do not use a stable-looking NVT temperature alone as proof of production-quality dynamics.
- If energy conservation is poor, likely candidates include loose SCF/grid thresholds, too-large timestep, poor initial structure, or insufficient equilibration.

## Restart / continuation pattern

Use only when the continuation semantics are clear.

Checks:

- Identify whether the user wants SCF restart, geometry/cell optimization continuation, MD continuation, or higher-level workflow continuation.
- Confirm referenced restart artifacts exist in the calculation directory or transfer manifest.
- Check project name, counters, coordinates, velocities for MD, thermostat/barostat state when relevant, and whether restart counters should continue.
- Preserve old restart files and avoid overwriting user evidence.

## Execution handoff pattern

Default to dry-run preparation.

Handoff content should include:

- Calculation directory inventory.
- Upload manifest and expected retrieval files.
- Recommended command shape such as `cp2k.psmp -i input.inp -o output.log`, without claiming the executable exists locally.
- Execution-environment assumptions: module name, CP2K version, data-library availability, scheduler, MPI layout, walltime, memory, and scratch policy when known.
- Required approval evidence before real execution: input validation, dry-run/plan, resource estimate, credential scan, file hashes, and explicit gate decision.

Do not submit local, remote, or HPC jobs from this skill without the SimFlow approval gate.

## Output review pattern

For returned results, inspect:

- Main log or output file for CP2K version, project, run type, normal end, abort/error lines, warnings, SCF convergence, final energy, and task-specific criteria.
- `.ener` for MD temperature, potential energy, conserved quantity, step count, and equilibration/production boundaries.
- Trajectory for frame count, final structure, atom count consistency, and suspicious jumps.
- Restart metadata for continuation readiness.

Do not record a calculation as completed or converged from scheduler completion alone.
