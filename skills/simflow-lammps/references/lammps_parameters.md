# LAMMPS Reference Index

This file is the compact entry point for `simflow-lammps`. It is not a LAMMPS
manual and must not override official LAMMPS documentation.

## Use These References

- `lammps_official_sources.md`: official documentation anchors.
- `lammps_input_validation.md`: static inspection contract for input/data/log/dump.
- `lammps_force_fields_and_mlp.md`: classical, reactive, KIM, and MLP deployment evidence.
- `lammps_md_workflows.md`: common MD workflow patterns and smoke/production boundaries.
- `lammps_output_intake.md`: LAMMPS output intake and analysis-stage handoff evidence.
- `lammps_troubleshooting.md`: common failures and minimum diagnostic evidence.

## Minimum Evidence

| Evidence | What To Look For |
| --- | --- |
| System definition | `read_data`, `read_restart`, or `create_box` + `create_atoms` |
| Unit convention | `units`; potential/model files may encode their own unit assumptions |
| Atom model | `atom_style` and matching data-file `Atoms` section |
| Force field | `pair_style`, `pair_coeff`, potential/model files, mixing rules, charge model |
| Dynamics or operation | `run`, `minimize`, or `rerun`; integration fixes for MD |
| Output | `thermo`, `thermo_style`, `dump`, `restart`, analysis `fix ave/time` |
| Included inputs | `include` files recorded and inspected as separate artifacts |
| Safety | dry-run evidence, credential scan, approval before real execution |

## Local Example Motifs

- `examples/melt/in.melt`: minimal LJ melt with `units lj`, `lj/cut`, `fix nve`.
- `examples/DIFFUSE/in.msd.2d`: MSD diffusion estimate after equilibration and `reset_timestep`.
- `examples/rdf-adf/in.spce`: RDF/ADF with `compute rdf/adf` and `fix ave/time`.
- `examples/rerun/in.rdf.rerun`: rerun-based post-processing from an existing dump.
- `examples/VISCOSITY/in.gk.2d`: Green-Kubo viscosity via `fix ave/correlate`.
- `examples/ELASTIC/in.elastic`: modular include files for units, potential, and displacements.

Use examples as motifs, not mandatory workflow branches.
