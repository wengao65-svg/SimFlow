# CP2K Troubleshooting

Use this reference when a user asks about failed CP2K runs, convergence, odd MD behavior, missing files, or suspicious output. Always inspect local evidence before prescribing fixes.

## First pass

- Inventory input decks, logs, `.ener`, trajectories, restart files, coordinate files, basis/potential files, topology files, and run scripts.
- Identify CP2K version, executable family, run type, project name, normal end or abort, warning count, and the last completed section.
- Compare the input task with the observed output. For example, `RUN_TYPE MD` without `.ener` output may be an output setup issue or an early failure.
- Keep conclusions scoped to evidence. A missing log or truncated output should produce a partial diagnosis, not a completed-result claim.

## SCF convergence

Common checks:

- `EPS_SCF`, `MAX_SCF`, `OUTER_SCF`, OT/diagonalization choice, preconditioner, smearing, mixing, spin state, charge, and restart guess.
- Metallic or small-gap systems may need smearing, diagonalization/mixing, additional MOs, or k-point review instead of a default OT setup.
- Bad initial structures, too-small cells, wrong charge/multiplicity, or inconsistent basis/potential choices can look like SCF problems.
- For restarts, check whether `SCF_GUESS RESTART` and restart files are compatible with the current input.

Report possible fixes as candidates tied to evidence. Avoid asserting that one keyword will solve the issue unless the log makes it clear.

## Cutoff and grid issues

The CP2K cutoff documentation emphasizes that `CUTOFF` controls the finest multigrid level and `REL_CUTOFF` controls mapping of Gaussian products to grid levels. Use the online CP2K manual, or `$CP2K_SOURCE_DIR/docs/methods/dft/cutoff.md` when the user provides a local source tree, when advising on grid convergence.

Checks:

- `MGRID/CUTOFF`, `MGRID/REL_CUTOFF`, `NGRIDS`, basis family, pseudopotential family, target property, and accuracy threshold.
- Whether a grid convergence test exists for the actual system and property, not just a generic water example.
- Whether force/stress convergence matters. MD, geometry optimization, cell optimization, and phonons require more than final energy stability.

## MD drift or unstable trajectories

Inspect `.ener` and trajectory evidence:

- Temperature trend, potential energy trend, conserved quantity, timestep, ensemble, thermostat/barostat constants, equilibration length, and production window.
- For NVE, energy drift and oscillation should be small relative to kinetic energy or the target temperature scale for the intended analysis.
- If drift is large, consider tighter `EPS_SCF`, tighter `QS/EPS_DEFAULT`, higher `MGRID/CUTOFF` or `REL_CUTOFF`, smaller timestep, better initial structure, or better equilibration.
- Do not use thermostatted trajectories alone to hide force-quality problems when the scientific claim depends on dynamics.

## Geometry and cell optimization

Checks:

- Geometry optimization completion requires all relevant CP2K criteria, not just a final coordinate file.
- For cell optimization, verify stress relevance, pressure units, cell degrees of freedom, symmetry constraints, and grid/basis sensitivity.
- If atoms move unphysically, inspect constraints, coordinate ordering, cell periodicity, force thresholds, and the starting structure.

## Missing basis, potential, topology, or coordinates

- Check whether file names in the input are symbolic library names available through the CP2K runtime, relative paths, or absolute paths.
- Do not copy basis or potential library contents into reports. Record names, source, and whether the file was found.
- For generated inputs, verify every element has an explicit `KIND` with basis and potential. The SimFlow generator has limited built-in defaults and may require `element_params`.
- For QMMM or force-field workflows, record topology/parameter provenance and do not expose proprietary content.

## Restart problems

- Check `EXT_RESTART`, `RESTART_FILE_NAME`, `RESTART_COUNTERS`, `SCF_GUESS`, project name, and whether the restart came from the same calculation family.
- For MD, check whether velocities and thermostat/barostat state are needed.
- For geometry/cell optimization, check whether the restart contains the intended latest structure and whether counters should continue.
- If the user only asks to "continue", ask what should continue: SCF, optimization, MD, or a higher-level workflow.

## Output parsing caveats

- A final energy is not proof of successful completion.
- `PROGRAM ENDED AT`, SCF convergence markers, geometry/cell optimization criteria, warning counts, abort/error lines, and truncated files matter.
- `.ener` column interpretation should be recorded with units. For common CP2K MD outputs, columns are step, time, kinetic energy, temperature, potential energy, conserved quantity, and CPU time per step.
