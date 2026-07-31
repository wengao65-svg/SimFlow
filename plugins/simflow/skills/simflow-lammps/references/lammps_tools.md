# LAMMPS Tools

LAMMPS-specific third-party tools for input preparation, output parsing,
and post-processing. For general-purpose tools (MDAnalysis, OVITO,
pymatgen, Matplotlib, pandas), see
`simflow-analysis-visualization/references/tooling_index.md`.

These tools are optional routes. They do not replace user scripts, official
LAMMPS examples, or SimFlow helpers. Record command, version, inputs,
outputs, environment, and limitations when used.

## LAMMPS Python interface

LAMMPS provides a Python package (`lammps`) for controlling simulations and
querying data from Python.

- Capabilities: run LAMMPS from Python, query thermo/dump data, control
  simulation flow, extract per-atom data, run multi-stage workflows
  programmatically.
- Documentation: https://docs.lammps.org/Python_head.html
- SimFlow context: record LAMMPS Python package version, LAMMPS
  executable build (`lmp -h` output), package configuration, and script
  provenance.
- Limitations: package availability depends on LAMMPS build configuration
  (compile flags, MPI, GPU packages). A LAMMPS build without Python
  support cannot use this interface.

## LAMMPS bundled tools

The LAMMPS distribution includes utility scripts for format conversion and
basic analysis in its `tools/` directory.

- Documentation: https://docs.lammps.org/Tools.html
- Common utilities: `ch2lmp` (CHARMM to LAMMPS conversion), `lmp2cfg`
  (dump to cfg), `micelle2d`, `bamboo`, and others depending on the
  distribution version.
- SimFlow context: record tool path, version, command, input/output
  files, and provenance.
- Prefer MDAnalysis or custom Python for new analysis work; bundled tools
  are useful for format interop with legacy workflows.

## Pizza.py

Legacy LAMMPS post-processing toolkit.

- Capabilities: dump file reading, basic trajectory analysis, plotting,
  simple statistics.
- SimFlow context: legacy tool; record if used; prefer MDAnalysis or
  custom Python for new work.
- Limitations: unmaintained; Python 2 era; limited format support;
  reduced compatibility with modern LAMMPS dump formats.

## General guidance

For LAMMPS output file roles and intake manifest, see
`lammps_output_intake.md`. For static input inspection checks, see
`lammps_input_validation.md`. For force-field and MLP deployment evidence,
see `lammps_force_fields_and_mlp.md`. For official LAMMPS documentation
entry points, see `lammps_official_sources.md`.
