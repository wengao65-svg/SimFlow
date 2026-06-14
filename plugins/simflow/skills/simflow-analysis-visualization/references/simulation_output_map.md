# Simulation Output Map

Use this reference when the available outputs, supported file types, or analysis
route are unclear. This map is a guide, not a fixed parser requirement.

## General intake

- Identify the software, run type, source directory, and whether files are raw outputs, derived data, or user-edited tables.
- Preserve original files. Write parsed tables, summaries, and plots as separate artifacts.
- Record missing predecessors such as restart files, charge densities, topology files, trajectory metadata, or line-mode path definitions.
- Treat user-provided CSV, JSON, text tables, and trajectories as generic inputs when software provenance is unknown.

## VASP outputs

- Common files: `OUTCAR`, `OSZICAR`, `vasprun.xml`, `vaspout.h5`, `CONTCAR`, `XDATCAR`, `DOSCAR`, `EIGENVAL`, `PROCAR`, `CHGCAR`, and `WAVECAR`.
- Common analyses: convergence and warnings, final energy, force and stress review, structure change, MD temperature and energy drift, DOS, band structure, PDOS, projected bands, and charge-density-derived views.
- Optional tools: SimFlow VASP helpers, pymatgen, ASE, py4vasp, PyProcar, VASPKIT-style community post-processing, shell extraction, or custom Python.
- For mature VASPKIT-style routes, load `community_postprocessing_tools.md` and confirm prerequisite files, task id, local config, generated data, command log, and figure lineage before treating tool output as evidence.
- Record POTCAR metadata only when needed. Do not copy, print, snapshot, or redistribute POTCAR contents.

## CP2K outputs

- Common files: `.out`, `.log`, `.ener`, `*-pos-*.xyz`, `*-frc-*.xyz`, `*.restart`, cell files, and user-defined print outputs.
- Common analyses: SCF convergence, total energy, cutoff or relative-cutoff series, final geometry, force review, MD temperature, conserved quantity drift, and trajectory-derived structure metrics.
- Optional tools: SimFlow CP2K helpers, ASE, pandas, custom parsers, notebooks, or user-provided CP2K tools.
- Record basis and potential file names or metadata when available, without copying large local libraries into reports.

## LAMMPS outputs

- Common files: `log.lammps`, `lammps.log`, thermo tables, dump trajectories, restart files, and `data.*` or `data.lammps` topology files.
- Common analyses: thermo time series, pressure/temperature/energy drift, density, RDF, MSD, diffusion, stress, strain, and structure snapshots.
- Optional tools: SimFlow LAMMPS parser, MDAnalysis, OVITO when available, pandas, Pizza.py-style tools, shell extraction, or custom Python.
- Confirm dump columns, timestep spacing, units style, atom ids, image flags, masses, and topology before interpreting trajectory-derived quantities.

## GPUMD outputs

- Common files include thermo, trajectory, force, velocity, modal, heat-current, and transport outputs defined by the GPUMD run commands.
- Common analyses: energy and temperature drift, structure snapshots, RDF/MSD when trajectories contain sufficient metadata, thermal conductivity, heat current, modal analysis, and machine-learning potential diagnostics.
- Common output files can include `thermo.out`, `dump.xyz`, `movie.xyz`, `msd.out`, `rdf.out`, `hac.out`, `kappa.out`, `sdc.out`, `viscosity.out`, `dos.out`, and modal or transport outputs depending on the GPUMD run commands.
- Optional tools: GPUMDkit, GPUMD/NepTrainKit ecosystem tools when available, numpy, pandas, ASE, MDAnalysis-compatible conversions, or custom Python.
- For GPUMDkit-style conversion, analyzer, calculator, or plotting routes, load `community_postprocessing_tools.md` and preserve generated `PLOT.in` or configuration files, derived data, figures, command logs, and skipped-tool reasons.
- Record command-line inputs, model or potential identifiers, output cadence, unit conventions, and any conversion scripts.

## Unsupported engine placeholders

- QE and Gaussian skills are reserved placeholders in the current SimFlow product. User-provided QE or Gaussian files can still be recorded as generic artifacts when the user asks for traceability.
- Do not claim supported QE or Gaussian runtime analysis. Use generic parsing or user-provided scripts only when evidence and limitations are recorded.

## Generic data and trajectories

- CSV/text tables: record delimiter, header interpretation, units, filters, and missing-value handling.
- JSON/HDF5: record selected keys, schema assumptions, and conversion scripts.
- Trajectories: record topology source, atom identity, periodic boundary handling, timestep, frame count, equilibration cut, production window, and unit conversions.

## Useful external references

- LAMMPS output guide: https://docs.lammps.org/Howto_output.html
- LAMMPS tools: https://docs.lammps.org/Tools.html
- GPUMD output files: https://gpumd.org/gpumd/output_files/index.html
