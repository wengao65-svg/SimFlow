# Analysis Methods

Use this reference when a result depends on numerical choices such as fit
windows, filtering, binning, equilibration cuts, or uncertainty estimates.

## Shared checks

- Start with a file manifest, source artifact ids, software or data provenance, unit conventions, and missing-output notes.
- Separate raw outputs, parsed data, derived data, plots, captions, and interpretation notes.
- Record warnings, unconverged states, failed frames, rejected points, and alternative interpretations.
- Do not infer completion from the presence of an output file alone. Check convergence, run termination, and expected frame or step counts.

## Property-Specific References

Use this file for shared numerical discipline. For full property contracts, use
the focused references:

- `md_structure_analysis.md`
- `md_diffusion_transport.md`
- `mechanical_elastic_analysis.md`
- `electronic_structure_analysis.md`
- `phonon_vibrational_analysis.md`
- `neb_barrier_analysis.md`
- `defect_surface_adsorption_analysis.md`
- `mlp_md_analysis_readiness.md`

## Energies, forces, and stress

- Energy convergence plots should record the energy column, step definition, unit, and whether values are electronic, ionic, thermo, potential, total, or free energies.
- Force and stress checks should report maxima or distributions when available, not only the final scalar energy.
- Geometry and cell optimization summaries should include initial and final structure references, displacement/cell change, convergence flags, and any restart semantics.
- For series studies, record consistent reference states and normalization choices such as per atom, per formula unit, per surface area, or relative energy.

## Structure and trajectory sanity checks

- Confirm atom identity, periodic boundary conventions, cell vectors, frame count, timestep, and unit conversions before computing trajectory-derived properties.
- Report equilibration and production windows separately. If no equilibration cut is applied, record that explicitly.
- For noisy time series, prefer block statistics or independent seeds when available. Single-trajectory results should be labeled as such.
- Missing frames, nonmonotonic timesteps, changing atom counts, broken topology, or inconsistent units should produce warnings or failure checkpoints.

## RDF, MSD, and diffusion

- RDF results should record selections, bin count, radial range, normalization, periodic boundary handling, and frame window.
- MSD results should record the atom selection, unwrapping or image handling, time origin strategy, time window, dimensionality, and fit interval.
- Diffusion coefficients should record the linear fit window, slope units, dimensionality factor, conversion to reported units, and uncertainty or sensitivity when available.
- Do not treat short trajectories, rare events, or single seeds as high-confidence diffusion evidence without caveats.

## Electronic-structure figures

- DOS, PDOS, bands, projected bands, and optical spectra should record Fermi-level alignment, energy zero, spin channel handling, smearing or broadening, projection definitions, and k-point path evidence.
- Band structures need the path labels and predecessor calculation context. DOS and PDOS need projection or orbital definitions.
- For VASP, py4vasp, pymatgen, PyProcar, VASPKIT, or custom parsers are optional routes; record the chosen route and limitations.

## Transport and time-correlation analyses

- Thermal conductivity, heat-current correlation, viscosity, vibrational spectra, and modal analyses should record sampling interval, correlation length, integration window, filtering, ensemble, and unit conversions.
- GPUMD or LAMMPS transport outputs should retain raw correlation or modal data beside final scalar summaries.
- Sensitivity to cutoff window or block size should be reported when it can change the conclusion.

## Acceptance for writing or handoff

- A result is ready for writing only when source data, script or notebook, parameters, environment note, figure or table artifact, and interpretation note are traceable.
- If the analysis supports only a qualitative trend or preliminary check, label it as such and avoid final-result language.
