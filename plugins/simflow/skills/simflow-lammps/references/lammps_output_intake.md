# LAMMPS Output Intake

This reference is for LAMMPS-specific output semantics before analysis. It is
not the final RDF, MSD, diffusion, transport, elastic, or visualization method
contract. Those property-level decisions belong to `simflow-analysis-visualization`.

## Intake Evidence

Record enough software-specific context for downstream analysis:

- log path, LAMMPS version when visible, run completion evidence, warnings, and errors.
- thermo columns, step spacing, units style, and whether values are potential, kinetic, total, pressure, stress, strain, or user-defined columns.
- dump path, style, frame count, atom count, timestep spacing, coordinate convention, atom ids, type/species mapping, image flags, and sorting.
- data/restart/topology source, masses, charges, molecule ids, bonds, and box/cell vectors when needed.
- force-field or MLP deployment manifest that generated the output, if available.

## Handoff Contract

Produce or request a `lammps_output_intake_manifest` with:

- source files and roles.
- parser/helper/tool used.
- columns and units detected.
- missing or ambiguous metadata.
- recommended analysis family such as MD structure, diffusion/transport, mechanical/elastic, or visualization.
- limitations that must be resolved before final scientific claims.

## Boundary

`simflow-lammps` may flag that output is insufficient for a proposed analysis,
for example missing atom ids or timestep metadata. It should not choose final
fit windows, block sizes, RDF bins, transport integration windows, elastic
moduli, figure claims, or publication wording. Route those choices to
`simflow-analysis-visualization`.
