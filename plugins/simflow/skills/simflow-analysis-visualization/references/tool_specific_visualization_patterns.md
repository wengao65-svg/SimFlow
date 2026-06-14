# Tool-Specific Visualization Patterns

Use this reference when the request needs a domain-specific plotting or
visualization tool rather than a generic Matplotlib figure. These are optional
routes, not fixed requirements. Choose the smallest tool path that preserves
evidence, works in the current environment, and can be recorded.

If a mature packaged post-processing suite such as GPUMDkit, VASPKIT, py4vasp,
PyProcar, Phonopy, sumo, OVITO, or a domain-local script already covers the
requested workflow, load `community_postprocessing_tools.md` first. Use this
file for lower-level headless rendering, conversion, and visualization patterns
after the community-tool route has been accepted, skipped, or ruled out.

## Shared pattern

- Inspect the input files and profile the data before choosing the tool.
- Prefer headless/scripted execution for reproducibility and remote/HPC
  friendliness.
- Record the executable or Python interpreter, command, script, environment,
  source files, generated files, skipped dependencies, warnings, and parent
  artifact ids.
- Use a generate -> render/export -> inspect -> adjust loop for visual outputs.
- Keep raw simulation outputs separate from derived meshes, converted
  trajectories, screenshots, movies, and figure manifests.

## Matplotlib, pandas, Plotly

- Use pandas/numpy/scipy for tabular parsing, transforms, fitting, statistics,
  and derived data tables.
- Use Matplotlib object-oriented plotting for publication static figures and
  vector export.
- Use Plotly only when interactive review artifacts are requested or useful.
  Record the HTML or JSON output as an exploratory or review artifact unless the
  final deliverable explicitly accepts interactive figures.

## ASE, pymatgen, MDAnalysis

- Use ASE for structure I/O, format conversion, simple trajectory handling, and
  geometry operations when atom identity and units are clear.
- Use pymatgen for materials structures, VASP parsing, DOS/band objects,
  crystallographic metadata, and composition or phase utilities.
- Use MDAnalysis for trajectory selections, RDF, MSD, diffusion-style analysis,
  and trajectory conversion when topology, timestep, units, and periodic
  boundary handling are recorded.

## py4vasp, PyProcar, VASPKIT-style tools

- Use py4vasp for supported VASP output formats and official Python workflows
  when available.
- Use PyProcar for projected bands, DOS, Fermi surfaces, and related
  electronic-structure plots when the input files are complete.
- Use `community_postprocessing_tools.md` for mature VASPKIT-style workflows,
  command capture, generated artifacts, local config assumptions, and citation
  notes. Do not copy or expose POTCAR contents.

## OVITO and ParaView-style routes

- Use OVITO Python for atomistic visualization or trajectory analysis when it is
  installed and the data format is supported. Record rendering settings and
  pipeline modifiers.
- Use ParaView or pvpython-style workflows for volumetric, mesh, field, or large
  scientific visualization tasks. Prefer batch/headless execution and record
  camera, coloring, filters, and screenshot settings.
- If a GUI-only route is required, request confirmation and record that the
  result depends on manual interaction.

## VMD, GROMACS, and molecular visualization

- Use VMD, vmd-python, or VMD text mode for molecular scenes when available.
  Record representations, selections, materials, camera settings, and renderer.
- Use MDAnalysis or GROMACS command-line tools for trajectory metrics when they
  match the available topology and trajectory files.
- For GROMACS-derived outputs, preserve `.xvg` or intermediate tables beside
  plotted summaries and record selection syntax.

## GPUMD and transport-style outputs

- Use `community_postprocessing_tools.md` first when GPUMDkit or another GPUMD
  ecosystem suite directly supports the requested conversion, analyzer,
  calculator, or plot.
- Use numpy/pandas or custom Python for thermo, heat-current, modal, velocity,
  force, and transport outputs when mature tools are unavailable or unsuitable.
- Record model or potential identifiers, sampling interval, correlation length,
  integration window, filtering, and unit conversions.
- Keep raw correlation or modal data beside final scalar summaries because
  window choices can change conclusions.
