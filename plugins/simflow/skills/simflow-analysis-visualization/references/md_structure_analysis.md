# MD Structure Analysis

Use this reference for trajectory structure metrics across AIMD, classical MD,
MLP-MD, LAMMPS, GPUMD, CP2K, VASP MD, ASE, or generic trajectories.

## Required Evidence

- trajectory source, topology/data file, atom identity, species/type mapping, cell vectors, frame count, timestep, and unit convention.
- equilibration and production windows, frame stride, and rejected frames.
- coordinate convention, periodic wrapping/unwrapping, image flags, and molecule reconstruction when relevant.

## Methods

- RDF/coordination: selections, species pairs, bin count, radial range, normalization, cutoff choice, and finite-size caveats.
- Structure recognition: CNA, PTM, centrosymmetry, Voronoi, clustering, hydrogen bonds, or project-specific descriptors with tool/version settings.
- Snapshots/movies: frame selection, camera/view settings, coloring, periodic images, and source-frame traceability.

## Claim Limits

Short or unequilibrated trajectories can support smoke checks or qualitative
structure inspection, not final phase, coordination, or ordering claims without
sampling and uncertainty evidence.
