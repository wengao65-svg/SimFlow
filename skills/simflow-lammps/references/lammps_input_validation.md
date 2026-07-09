# LAMMPS Input Validation

Static validation supports dry-run readiness only. It does not prove the input
will run, conserve energy, equilibrate, or support scientific claims.

## Input Script

Check and record:

- `units`, `dimension`, `boundary`, `atom_style`.
- System source: `read_data`, `read_restart`, or `create_box` plus `create_atoms`.
- `pair_style`, `pair_coeff`, `bond_style`, `angle_style`, `kspace_style` when relevant.
- MD operation: `minimize`, `run`, or `rerun`.
- Integration fixes for MD: `nve`, `nvt`, `npt`, `nph`, `langevin`, or project-specific alternatives.
- `thermo`, `thermo_style`, `dump`, `restart`, `write_data`, `write_restart`.
- `include`, `variable`, shell paths, absolute paths, and environment-dependent tokens.

## Data File

Check and record:

- atom count, atom types, box bounds, masses, `Atoms` section style.
- consistency between `atom_style` and `Atoms` section.
- charge columns for charged/reactive styles.
- molecule IDs, bonds, angles, dihedrals, impropers when molecular topology is used.

## Output Evidence

For logs, capture LAMMPS errors/warnings, thermo row count, loop-time presence,
and whether the run completed. For dumps, verify atom identity (`id` or stable
sorting), type, coordinates, and enough frames for the intended analysis.

## Findings

Use structured findings with `severity`, `code`, `message`, `evidence`, and
`remediation` when possible. Missing files or missing core input sections block
readiness; undocumented provenance, missing statistics, and package uncertainty
should remain warnings unless they make interpretation impossible.
