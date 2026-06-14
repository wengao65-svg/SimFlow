---
name: simflow-analysis-visualization
description: Use when a user asks to analyze simulation outputs, write analysis scripts, or create traceable figures.
---

# SimFlow Analysis Visualization

## Trigger conditions

- The user provides completed outputs, partial outputs, tables, logs, trajectories, or figure requirements.
- The current research intent is analysis, visualization, uncertainty checking, convergence assessment, or figure preparation.
- A writing or handoff task needs results that trace back to data and scripts.

## Input conditions

- Simulation outputs, literature data, model artifacts, analysis goals, prior checkpoints, or user-provided datasets.
- Optional user preferences for Python packages, plotting style, statistical method, or figure format.
- The agent may use SimFlow helpers, self-written Python, domain libraries, notebooks, shell tools, or external packages available in the environment.
- Built-in analysis and visualization stage runners are optional reference routes for common energy-style traces, not the only valid analysis or figure path.
- Missing optional plotting or analysis dependencies are allowed. Record the skipped dependency and choose another traceable route when possible.

## Output artifacts

- Analysis script, command log, environment note, input data reference, derived data, validation report, and figures or captions.
- Interpretation notes that distinguish measured/calculated results from speculation.
- Figure lineage linking each visual to source data and script artifacts.

## Status write rules

- Register analysis scripts, commands, inputs, outputs, figures, and captions as artifacts under `project_root`.
- Link conclusions to upstream literature, model, computation, derived data, or figure artifacts.
- Record incomplete, missing, unconverged, or suspect outputs explicitly instead of smoothing them into final results.
- Resolve explicit `project_root` before writing `.simflow/` state, artifacts, checkpoints, reports, figure manifests, or lineage records.
- When figure styling, filtering, fitting, binning, or normalization choices affect interpretation, record the choice as analysis metadata.

## Working procedure

1. Read `.simflow/state/` before acting and resolve `project_root` explicitly before any SimFlow write.
2. Classify the request as data intake/profiling, output inspection, data extraction, chart selection, statistical analysis, trajectory analysis, electronic-structure plotting, tool-specific visualization, publication figure QA, troubleshooting, writing support, or handoff.
3. Inspect available local files before selecting a parser, plotting library, community post-processing suite, or custom script. Load `references/data_intake_and_profiling.md` for input typing, sample/frame/step counts, missing values, units, grouping, raw-vs-derived boundaries, and analysis readiness checks. Load `references/simulation_output_map.md` when output type, software provenance, or supported file coverage is unclear.
4. For quantitative methods, load `references/analysis_methods.md` and record windows, filters, fit ranges, uncertainty choices, rejected data, and alternative interpretations explicitly.
5. For figure construction, first load `references/figure_contract_and_visual_qa.md` when the figure supports a scientific claim, publication deliverable, caption, or visual handoff. Then load `references/plotting_principles.md` and preserve source data, script or notebook, environment, figure files, preview/review notes, and caption evidence.
6. For mature community post-processing routes such as GPUMDkit, VASPKIT-style optional tools, py4vasp, PyProcar, Phonopy, sumo, OVITO, or domain-local scripts, load `references/community_postprocessing_tools.md` before treating tool output as analysis evidence.
7. For tool choice, dependency questions, headless rendering, or lower-level domain-specific visualization, load `references/tooling_index.md` and, when needed, `references/tool_specific_visualization_patterns.md`. Treat SimFlow helpers, Matplotlib, pandas, ASE, pymatgen, MDAnalysis, py4vasp, PyProcar, Plotly, GPUMD tools, OVITO, ParaView, VMD, GROMACS, notebooks, shell commands, and custom Python as optional routes.
8. Register outputs as artifacts with metadata and lineage when writing intake profiles, analysis reports, derived data, community-tool command logs, helper-run manifests, figures, figure manifests, captions, visual QA notes, or handoff material.

## Reference map

- `references/plotting_principles.md`: Publication-quality figure preparation, Matplotlib object-oriented plotting, style sheets, export formats, fonts, units, color, accessibility, and figure provenance.
- `references/simulation_output_map.md`: Output-file recognition and recommended analysis routes for VASP, CP2K, LAMMPS, GPUMD, generic tables, generic JSON, and trajectories.
- `references/analysis_methods.md`: Energy convergence, force and stress checks, structure and trajectory sanity checks, RDF, MSD, diffusion, equilibration windows, blocking, DOS, bands, PDOS, transport, and uncertainty.
- `references/data_intake_and_profiling.md`: EDA-first intake for raw outputs, tables, trajectories, source/provenance, sample/frame/step counts, units, missing values, grouping, outliers, and raw-vs-derived boundaries before plotting or fitting.
- `references/community_postprocessing_tools.md`: Adapter protocol for mature community post-processing tools such as GPUMDkit, VASPKIT-style optional tools, py4vasp, PyProcar, Phonopy, sumo, OVITO, and domain-local scripts, including availability checks, command capture, citations, generated artifacts, and fallbacks.
- `references/figure_contract_and_visual_qa.md`: Claim-driven figure contract, chart-selection rationale, figure manifest expectations, preview inspection, visual QA, and revision-loop recording.
- `references/tool_specific_visualization_patterns.md`: Optional headless and domain-specific visualization patterns for Matplotlib/Plotly, ASE/pymatgen/MDAnalysis, py4vasp/PyProcar, OVITO/ParaView, VMD/GROMACS, and GPUMD-style tools.
- `references/tooling_index.md`: Optional analysis and plotting tools, dependency handling, helper-run recording, and when to use domain-specific packages.

## Checkpoint rules

- Create a checkpoint when an analysis dataset or figure set is ready for review, handoff, or writing.
- Create a failure checkpoint when parsing, validation, convergence, or reproducibility checks fail.

## Prohibited actions

- Do not fabricate data, plots, convergence status, statistics, or physical interpretation.
- Do not require a fixed parser, plotting library, output schema, report filename, or built-in SimFlow helper.
- Do not hide failed calculations, missing timesteps, failed frames, or statistical uncertainty.
- Do not manually edit figures in a way that disconnects them from recorded source data, scripts, commands, or figure manifests.
- Do not install missing optional plotting or analysis packages unless the user explicitly approves dependency installation.
- Do not install or require community post-processing suites such as GPUMDkit or VASPKIT unless the user explicitly approves that dependency path.
- Do not skip intake/profile checks and jump directly to a plot when the source data, units, grouping, frame/step counts, or analysis window are still ambiguous.

## Manual confirmation scenarios

- Analysis choices materially affect conclusions, such as filtering, fitting window, binning, normalization, equilibration cut, block size, or uncertainty model.
- Outputs are incomplete, unconverged, contradictory, missing source files, missing frames, or inconsistent with the proposed calculation.
- Optional dependencies are unavailable and the alternative route changes analysis scope or figure quality.
- A community post-processing suite is missing, interactive-only, locally configured, or would change the analysis scope compared with a custom script or domain library.
- The user needs publication-quality figure conventions, journal-specific formatting, a specific visual style, or a figure revision that changes the supported claim.
