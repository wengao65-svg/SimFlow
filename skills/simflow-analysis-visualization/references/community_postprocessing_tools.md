# Community Post-Processing Tools

Use this reference when a mature community tool may already implement the
requested post-processing or plotting workflow. Examples include GPUMDkit,
VASPKIT-style optional tools, py4vasp, PyProcar, Phonopy, sumo, OVITO, and
project-local scripts maintained by a research community.

These tools are optional routes. They are useful when they directly support the
raw outputs and standard analysis requested by the user, but they do not replace
SimFlow evidence rules or make any parser, plotter, or package mandatory.
If a future SimFlow helper supports these routes, prefer a command-manifest
recorder that captures the external tool invocation and outputs over a
strongly-bound runner for each community package.

## Adapter protocol

1. Profile the inputs first with `data_intake_and_profiling.md` and identify
   software provenance with `simulation_output_map.md`.
2. Check tool availability without installing anything: executable path, import
   availability, `--help`, version output, local config path, or documented
   command entry point.
3. Match required inputs to available files before running or recommending the
   tool. Record missing files, incompatible formats, and local configuration
   assumptions.
4. Prefer command-line or scripted modes for traceable runs. Treat interactive
   modes as manual review routes unless the user explicitly asks for them.
5. Record executable path, version/help output when practical, command, cwd,
   environment variables, config files, raw inputs, generated data, figures,
   stdout/stderr or command log, warnings, citation/license note, and parent
   artifact ids.
6. Treat generated plots and tables as derived artifacts. Do not call them final
   evidence until the figure contract, source data, parameters, caption evidence,
   and visual QA are connected.
7. If the tool is missing or unsuitable, record `skipped_optional_dependency` or
   `skipped_community_tool` and choose a traceable fallback such as custom
   Python, SimFlow helpers, or domain libraries.

## When to prefer mature tools

- The requested analysis is a standard workflow the community tool already
  implements, such as GPUMD transport plots, VASP DOS/bands, projected bands,
  charge-density-derived data, phonon plots, or common MD diagnostics.
- The raw outputs and prerequisite files match the tool's expected file names
  and formats.
- The tool produces intermediate data that can be preserved beside figures.
- The user has named the tool or the project already relies on it.

Prefer custom Python or a lower-level domain library when the workflow needs
nonstandard parsing, unusual fitting windows, stricter uncertainty analysis,
publication-specific styling, cross-tool validation, or a minimal dependency
surface.

## GPUMDkit route

GPUMDkit is a community toolkit for GPUMD and NEP workflows. It provides
interactive and command-line modes for conversion, analysis, calculation, and
visualization.

Common command families:

- Conversion examples: `gpumdkit.sh -out2xyz`, `gpumdkit.sh -lmp2exyz`, and
  related format-conversion commands.
- Analyzer examples: `gpumdkit.sh -range`, `gpumdkit.sh -min_dist_pbc`,
  `gpumdkit.sh -analyze_comp`, and outlier or composition checks.
- Calculator examples: `gpumdkit.sh -calc ...` routes for supported derived
  quantities.
- Plot examples: `gpumdkit.sh -plt thermo`, `msd`, `rdf`, `emd`, `nemd`,
  `hnemd`, `pdos`, `train`, `prediction`, force-error plots, and Arrhenius-style
  plots when supported by the installed version.

Record GPUMD inputs such as `run.in`, model or potential identifiers, thermo
and trajectory outputs, output cadence, units, conversion scripts, generated
`PLOT.in` or plotting config files, and all generated tables or figures.

Useful references:

- https://github.com/zhyan0603/GPUMDkit
- https://zhyan0603.github.io/GPUMDkit/htmls/plot_scripts.html
- https://gpumd.org/gpumd/output_files/index.html

## VASPKIT-style route

VASPKIT is a mature VASP post-processing suite with interactive, batch, and
command-style use patterns. It is useful for common VASP post-processing such as
DOS, band structures, projected bands, charge density, potential, optical,
transport, MD, Fermi-surface, and auto-plot workflows.

Common command patterns:

- `vaspkit -task <task_id>` when the installed version supports the selected
  task directly.
- `echo ... | vaspkit` for scripted interactive selections.
- `vaspkit < cmd.in` or a documented `cmd.in`/batch mode when a workflow needs
  reproducible multi-step selections.

Before using VASPKIT, confirm required VASP files are present for the requested
task, such as `vasprun.xml`, `OUTCAR`, `EIGENVAL`, `PROCAR`, `DOSCAR`, `CHGCAR`,
`LOCPOT`, `KPOINTS`, or structure files. Record local configuration assumptions
such as `~/.vaspkit`, task id, command log, generated data files, generated plot
scripts, and version when practical.

Keep POTCAR-related or input-generation tasks out of the analysis layer unless
the user explicitly asks and the safety gate is satisfied. Never copy, print,
snapshot, or redistribute POTCAR contents.

Useful references:

- https://vaspkit.com/
- https://vaspkit.com/features.html
- https://vaspkit.com/installation.html

## Citation, license, and reproducibility notes

- Preserve the tool name, version, citation recommendation, license constraints
  when known, and any manual edits to generated inputs or style files.
- If a community tool auto-generates plots, keep both its derived data and the
  rendered image. A SimFlow publication figure may still need a separate
  scripted styling pass and visual QA.
- If the community-tool result disagrees with a custom script or another
  library, do not smooth over the discrepancy. Record both routes, compare input
  assumptions, and mark the result as review-needed.
