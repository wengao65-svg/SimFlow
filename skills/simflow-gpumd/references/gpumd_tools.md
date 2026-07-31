# GPUMD/NEP Tools

GPUMD/NEP-specific third-party tools for input preparation, conversion,
analysis, calculation, plotting, training assistance, and inference. For
general-purpose tools (ASE, pymatgen, MDAnalysis), see
`simflow-analysis-visualization/references/tooling_index.md`.

These tools are optional routes and are tracked_only in the SimFlow
toolchain contract. SimFlow does not execute them. Record command,
version, inputs, outputs, environment, and limitations when used.

## GPUMDkit

Community toolkit for GPUMD and NEP workflows. Provides interactive and
command-line modes for conversion, analysis, calculation, and
visualization.

Common command families:

- Conversion: `gpumdkit.sh -out2xyz`, `gpumdkit.sh -lmp2exyz`, and
  related format-conversion commands.
- Analyzer: `gpumdkit.sh -range`, `gpumdkit.sh -min_dist_pbc`,
  `gpumdkit.sh -analyze_comp`, and outlier or composition checks.
- Calculator: `gpumdkit.sh -calc ...` routes for supported derived
  quantities.
- Plot: `gpumdkit.sh -plt thermo|msd|rdf|emd|nemd|hnemd|pdos|train|
  prediction|force-error|arrhenius` when supported by the installed
  version.

References:
- https://github.com/zhyan0603/GPUMDkit
- https://zhyan0603.github.io/GPUMDkit/htmls/plot_scripts.html
- https://gpumd.org/gpumd/output_files/index.html

SimFlow context:
- Record GPUMD inputs such as `run.in`, model or potential identifiers,
  thermo and trajectory outputs, output cadence, units, conversion
  scripts, generated `PLOT.in` or plotting config files, and all generated
  tables or figures.
- Treat GPUMDkit outputs as derived artifacts; preserve raw correlation or
  modal data beside final scalar summaries because window choices can
  change conclusions.
- Use `community_postprocessing_tools.md` adapter protocol for command
  capture, citation, and reproducibility notes when invoking GPUMDkit as a
  community tool.

Limitations:
- Command coverage is version-sensitive; verify the installed version
  supports the requested command.
- Interactive modes are manual review routes unless scripted.

## neptrain

Independent community training assistant for NEP workflows. Distinct from
`neptrainkit` and from the core GPUMD `nep` trainer.

- Capabilities: dataset preparation assistance, training orchestration,
  loss diagnostics, training-run inspection.
- SimFlow context: tracked_only (registered in `capabilities.json`).
  Record the actual tool used, version, command, dataset lineage, and
  training config provenance.
- Do not treat community training policies, loss schedules, or
  hyperparameter recommendations as NEP defaults or as required NEP
  methodology.
- Distinct from `neptrainkit` and from the GPUMD-bundled `nep` trainer;
  identify the actual trainer before interpreting optimization, scheduler,
  or restart evidence.

## neptrainkit

Community NEP training kit. Distinct from `neptrain` and from the core
GPUMD `nep` trainer.

- Capabilities: NEP dataset preparation, training orchestration, loss and
  training diagnostics, prediction helpers.
- SimFlow context: tracked_only (registered in `capabilities.json`).
  Record provenance without claiming SimFlow execution support.
- Identify the actual trainer before interpreting training evidence; do
  not treat neptrainkit's policies as NEP defaults.

## calorine

NEP ONNX inference and analysis library for trained NEP models.

- Capabilities: energy, force, and stress prediction from trained NEP
  models without running GPUMD MD; model introspection; prediction outside
  the MD runtime.
- SimFlow context: tracked_only (registered in `capabilities.json`).
  Record model file, ONNX export provenance, prediction context, and
  calorine version.
- Useful for MLP analysis-stage inference, model comparison, and
  prediction workflows that do not require an MD run.
- Do not claim production readiness, transferability, or model quality
  from calorine predictions alone; validation evidence must come from
  `simflow-mlp` readiness checks.

## General guidance

For GPUMD output file roles, see `gpumd_file_map.md`. For selected output
parsing scope and limits, see `gpumd_selected_output_parsing.md`. For
official GPUMD/NEP documentation entry points, see
`gpumd_official_sources.md`.
