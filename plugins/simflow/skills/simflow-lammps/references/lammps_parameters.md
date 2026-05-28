# LAMMPS Domain Assistant Notes

This reference is a compact inspection guide for SimFlow helpers. It is not a
LAMMPS manual.

## Official Documentation Anchors

- Command overview: https://docs.lammps.org/Commands.html
- Units: https://docs.lammps.org/units.html
- Timestep: https://docs.lammps.org/timestep.html
- NVT/NPT/NPH fixes: https://docs.lammps.org/fix_nh.html
- Dump output: https://docs.lammps.org/dump.html
- MSD/RDF: https://docs.lammps.org/compute_msd.html and https://docs.lammps.org/compute_rdf.html
- Averaged output: https://docs.lammps.org/fix_ave_time.html

## Minimum Evidence To Check

| Evidence | What To Look For |
| --- | --- |
| System definition | `read_data`, `read_restart`, or `create_box` + `create_atoms` |
| Unit convention | `units`; potential files may encode their own unit assumptions |
| Atom model | `atom_style` and matching data-file `Atoms` section |
| Force field | `pair_style`, `pair_coeff`, potential files, mixing rules, charge model |
| Dynamics or operation | `run`, `minimize`, or `rerun`; integration fixes for MD |
| Output | `thermo`, `thermo_style`, `dump`, `restart`, analysis `fix ave/time` |
| Included inputs | `include` files must be recorded and inspected as separate artifacts |
| Safety | dry-run evidence, credential scan, approval before real submit |

## Local Example Motifs Observed

The local LAMMPS 22Jul2025 examples show useful motifs to recognize:

- `examples/melt/in.melt`: minimal LJ melt with `units lj`, `lj/cut`, `fix nve`.
- `examples/DIFFUSE/in.msd.2d`: MSD diffusion estimate after equilibration and `reset_timestep`.
- `examples/rdf-adf/in.spce`: RDF/ADF with `compute rdf/adf` and `fix ave/time`.
- `examples/rerun/in.rdf.rerun`: rerun-based post-processing from an existing dump.
- `examples/VISCOSITY/in.gk.2d`: Green-Kubo viscosity via `fix ave/correlate`.
- `examples/ELASTIC/in.elastic`: modular include files for units, potential, and displacements.

Use these as pattern references, not as mandatory workflow branches.

## Review Heuristics

- Large timestep values are not automatically invalid, but they need review
  against `units`, potential convention, constraints, and target ensemble.
- Dump output used for trajectory analysis should preserve atom identity with
  atom IDs or stable sorting and include usable coordinates.
- Modular scripts using `include` should keep each included file in the artifact
  registry; a top-level input alone is not enough evidence.
- MSD/VACF/viscosity estimates need an equilibration boundary and statistical
  sampling discussion. A short example run is not enough for a final claim.
- Reactive or charge-transfer force fields often require explicit charge
  equilibration review.
- Potential files can be proprietary or installation-local. Record provenance
  and hashes when allowed, but do not vendor restricted content.

## Artifact Suggestions

- input script and data file
- force-field provenance note
- static inspection or validation report
- dry-run report and resource estimate before execution
- credential scan
- log and dump files if execution happened
- analysis script, output data, plots, and claim map if conclusions are written
