# Tooling Index

Use this reference when choosing an analysis or plotting tool. The tools below
are optional routes. Missing dependencies should be recorded as skipped reasons,
not treated as evidence that the analysis result exists.

## Environment audit note format

Treat environment inventories as project-local audit records, not durable skill
facts. Before relying on a plotting library, domain parser, or external command,
capture a fresh note with:

- interpreter or executable path
- package or command version/help output when practical
- package availability and missing optional dependencies
- command path, local config files, and relevant environment variables
- source files used by the audit and any generated probe outputs
- skipped reason when a dependency is absent, interactive-only, or unsuitable

Store checkout-specific facts under project reports or helper-run manifests
rather than in this distributable reference.

## Plotting and tables

- Matplotlib: default static plotting route for publication figures, multi-panel layouts, exported vector graphics, and scripted styling.
- pandas: useful for CSV/text tables, thermo logs after parsing, grouping, joins, and derived tables.
- numpy/scipy: useful for numerical transforms, fitting, smoothing with recorded parameters, integration, statistics, and signal analysis.
- Plotly: useful for interactive review artifacts when the user asks for interactivity or exploratory dashboards.
- seaborn: optional styling/statistical plotting layer when available. Do not require it for any figure.

## Atomistic and materials analysis

- ASE: useful for structure I/O, simple trajectory handling, geometry operations, and format conversion.
- pymatgen: useful for materials structures, VASP parsing, DOS/band objects, phase or composition utilities, and crystallographic metadata.
- MDAnalysis: useful for trajectory selections, RDF, MSD, diffusion-style analysis, and trajectory conversion when topology and units are clear.
- freud: optional particle and trajectory analysis library when available. Record skipped dependency when absent.
- OVITO Python: optional atomistic visualization and trajectory analysis route when available. Record skipped dependency when absent.

## Electronic-structure post-processing

- py4vasp: optional VASP analysis route for supported VASP output formats and official Python workflows.
- PyProcar: optional projected band, DOS, Fermi surface, and related electronic-structure plotting route.
- VASPKIT or other local tools: optional user-selected tools. Record command, version if available, input files, generated outputs, and limitations.

## Community post-processing suites

Load `community_postprocessing_tools.md` before using mature external suites as
analysis evidence. These tools can save time, but they remain optional derived
routes rather than required SimFlow parsers.

- GPUMDkit: optional GPUMD/NEP conversion, analyzer, calculator, and plotting
  suite for thermo, MSD, RDF, EMD/NEMD/HNEMD, PDOS, NEP training, prediction,
  force-error, and Arrhenius-style outputs when supported by the installed
  version.
- VASPKIT: optional VASP post-processing suite for DOS, bands, projected bands,
  charge density, potential, optical, transport, MD, Fermi-surface, and auto-plot
  workflows. Keep POTCAR/input-generation tasks outside analysis unless the user
  explicitly asks and safety gates are satisfied.
- py4vasp, PyProcar, sumo, Phonopy, OVITO, and domain-local scripts: optional
  community or project routes when their input requirements match the available
  files.
- Missing or unsuitable tools should be recorded as `skipped_optional_dependency`
  or `skipped_community_tool`, followed by a traceable fallback.

## Simulation-specific helpers

- SimFlow helper scripts: useful for built-in stage-runner evidence and helper-run manifests. They are optional helpers, not the only valid analysis path.
- GPUMD tools: optional route for GPUMD-specific outputs, transport analyses, and NEP-related diagnostics when available in the user's environment.
- LAMMPS tools and custom scripts: useful when dump columns, units style, or thermo output require project-specific parsing.
- CP2K tools and custom scripts: useful when output print settings or project-specific trajectories go beyond the common parser surface.

## Dependency handling

- Check availability before choosing a tool for a required deliverable.
- Do not install packages unless the user explicitly approves dependency installation.
- If a preferred tool is absent, choose a traceable fallback or record `skipped_optional_dependency` with the missing package and affected analysis scope.
- Record the executable, Python interpreter, package versions when practical, command line, source files, output files, and parent artifact ids.
