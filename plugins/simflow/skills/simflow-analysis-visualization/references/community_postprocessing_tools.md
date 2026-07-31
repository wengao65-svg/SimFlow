# Community Post-Processing Tools

Use this reference when a mature community tool may already implement the
requested post-processing or plotting workflow. Examples include py4vasp,
PyProcar, Phonopy, sumo, OVITO, and project-local scripts maintained by a
research community. Engine-specific community tools such as GPUMDkit and
VASPKIT have dedicated route references in their domain skills (see
"Engine-specific community routes" below).

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

## Engine-specific community routes

Detailed command families, prerequisite files, and SimFlow context for
engine-specific community tools live with their domain skills:

- GPUMDkit route: see `simflow-gpumd/references/gpumd_tools.md`.
- VASPKIT-style route: see `simflow-vasp/references/vasp_tools.md`.

The adapter protocol above still applies when invoking these tools: capture
command, version, inputs, outputs, environment, citations, and license notes.
Keep POTCAR-related or input-generation tasks out of the analysis layer
unless the user explicitly asks and the safety gate is satisfied. Never
copy, print, snapshot, or redistribute POTCAR contents.

## Citation, license, and reproducibility notes

- Preserve the tool name, version, citation recommendation, license constraints
  when known, and any manual edits to generated inputs or style files.
- If a community tool auto-generates plots, keep both its derived data and the
  rendered image. A SimFlow publication figure may still need a separate
  scripted styling pass and visual QA.
- If the community-tool result disagrees with a custom script or another
  library, do not smooth over the discrepancy. Record both routes, compare input
  assumptions, and mark the result as review-needed.
