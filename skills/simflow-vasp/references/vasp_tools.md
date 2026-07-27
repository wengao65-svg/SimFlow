# VASP Tools

VASP-specific third-party tools for input preparation, output parsing, and
post-processing. For general-purpose tools (ASE, pymatgen, MDAnalysis,
packmol, Matplotlib), see
`simflow-analysis-visualization/references/tooling_index.md`.

These tools are optional routes. They are not the only valid path and do not
replace user scripts, official VASP workflows, or SimFlow helpers. Record
command, version, inputs, outputs, environment, and limitations when used.

## py4vasp

Official VASP Python library maintained by the VASP team. Use it for
supported VASP output formats and official Python workflows when available.

- Capabilities: read `OUTCAR`, `vasprun.xml`, `vaspout.h5`, `DOSCAR`,
  `EIGENVAL`, `PROCAR`, `CHGCAR`; compute DOS, band structures, charge
  densities, projected quantities; query INCAR parameters; band
  interpolation support.
- Documentation: https://www.vasp.at/py4vasp/latest/
- `vaspout.h5` reference: https://www.vasp.at/wiki/Vaspout.h5

SimFlow context:
- Record py4vasp version, VASP version that produced the inputs, and access
  pattern (file path, calc object, or H5 file).
- `vaspout.h5` is required for full feature coverage; older text outputs
  have a reduced API surface.
- Treat py4vasp output as derived evidence; preserve source VASP files and
  the script or notebook used.

Limitations:
- Version-sensitive API; functions and signatures can change between
  releases.
- Reading large `vasprun.xml` or `OUTCAR` files can be slow; prefer
  `vaspout.h5` when available.

## VASPKIT

Community VASP pre/post-processing toolkit with interactive, batch, and
command-line use patterns.

- Capabilities: structure generation, k-mesh generation, DOS, band
  structures, projected bands, charge density, potential, optical spectra,
  transport, MD post-processing, Fermi surface, and auto-plot workflows.
- Documentation: https://vaspkit.com/
- Feature list: https://vaspkit.com/features.html
- Installation: https://vaspkit.com/installation.html

Common command patterns:
- `vaspkit -task <task_id>` when the installed version supports the
  selected task directly.
- `echo ... | vaspkit` for scripted interactive selections.
- `vaspkit < cmd.in` or a documented `cmd.in`/batch mode when a workflow
  needs reproducible multi-step selections.

Prerequisite files (task-dependent): `vasprun.xml`, `OUTCAR`, `EIGENVAL`,
`PROCAR`, `DOSCAR`, `CHGCAR`, `LOCPOT`, `KPOINTS`, or structure files.
Confirm required VASP files are present for the requested task before
running or recommending VASPKIT.

SimFlow context:
- Record executable path, version when practical, task id, command log,
  local config assumptions such as `~/.vaspkit`, generated data files,
  generated plot scripts, and parent artifact ids.
- Keep POTCAR-related or input-generation tasks out of the analysis layer
  unless the user explicitly asks and the safety gate is satisfied.
- Treat VASPKIT plots and tables as derived artifacts; preserve both
  derived data and rendered images, plus the command log.

Prohibited:
- Do not use VASPKIT to generate, copy, print, snapshot, or redistribute
  POTCAR content.
- Do not treat VASPKIT as the only valid VASP post-processing path; user
  scripts, py4vasp, pymatgen, or custom Python are acceptable when
  evidence and lineage are recorded.

Limitations:
- Task id coverage and behavior vary by VASPKIT version; verify the
  installed version supports the requested task.
- Interactive modes are manual review routes unless explicitly scripted.
- Local config (`~/.vaspkit`) can change outputs; record config provenance.
