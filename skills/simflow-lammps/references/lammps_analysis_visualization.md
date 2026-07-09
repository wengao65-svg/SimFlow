# LAMMPS Analysis And Visualization

Analysis must preserve the path from raw output to claim. A plot or scalar is
not enough without source files, code, parameters, and uncertainty notes.

## Log And Trajectory Intake

Record:

- log path, run completion evidence, thermo columns, warnings/errors.
- dump path, frame count, atom count, timestep/unit provenance, coordinate convention.
- equilibration frames excluded from analysis.
- selection strings and type/species mapping.

## Common Analyses

- RDF/coordination: binning, cutoff, species pairs, finite-size caveats.
- MSD/diffusion: time origin, dimensionality, fit window, unit conversion, block uncertainty.
- VACF/transport: correlation length, sampling length, averaging method.
- viscosity/thermal conductivity: Green-Kubo or NEMD protocol and error bars.
- elastic/deformation: strain definition, stress convention, cell control.
- structure recognition: OVITO CNA/PTM/centrosymmetry/voronoi settings.

## Claim Discipline

Short examples or smoke trajectories can validate a script path, not a final
transport or phase-transition claim. If there is no uncertainty estimate, say
so and keep the claim qualitative or preliminary.
