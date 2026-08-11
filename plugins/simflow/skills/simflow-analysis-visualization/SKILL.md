---
name: simflow-analysis-visualization
description: Guide evidence-bounded simulation analysis, statistics, interpretation, and traceable scientific figures.
---

# Analysis And Visualization

## Purpose

Help the agent derive and communicate scientific results without allowing a
plotting choice, parser success, or attractive figure to substitute for valid
analysis.

## Use when

- Inspecting simulation outputs, tables, trajectories, logs, or derived data.
- Computing statistics, convergence measures, physical observables, or figures.
- Comparing runs, methods, models, or literature benchmarks.

## Do not use when

- The current task is primarily running a new calculation.
- The user only asks for manuscript prose from already accepted results.

## Task principles

- Define the scientific question before choosing a plot or metric.
- Preserve the relationship from raw input through processing to figure data.
- Check units, normalization, sampling, grouping, and missing data before fitting.
- Record windows, filters, smoothing, binning, fits, exclusions, and uncertainty
  choices when they affect interpretation.
- Distinguish numerical failure, outlier, insufficient sampling, and plausible
  physical behavior.
- Do not edit a figure in a way that changes scientific meaning without a
  reproducible source-data transformation.

## Minimum checks

- Input type, provenance, sample/frame/step count, units, and completeness are
  understood.
- Equilibration and analysis windows are justified.
- Statistical comparisons identify samples, uncertainty, and dependence.
- The selected visual encoding supports the intended claim.
- Key numerical values agree across tables, figures, and text.
- Alternative interpretations and evidence limitations are stated.

## Common failure modes

- Plotting before checking units, grouping, or missing frames.
- Inferring convergence from a smooth curve alone.
- Reporting a fitted value without window sensitivity or uncertainty.
- Treating correlation as mechanism or causation.
- Hiding failed runs because they make a figure less clean.
- Using normalization or smoothing that changes the apparent conclusion.

## Escalate uncertainty when

- Filtering, fitting, binning, normalization, or uncertainty choices materially
  change the conclusion.
- Outputs are incomplete, unconverged, contradictory, or missing provenance.
- Publication requirements change the supported scientific claim.

## Completion criteria

- The result answers a stated question and remains traceable to source data and
  reproducible processing.
- Uncertainty and limitations are visible.
- Figures and summaries do not claim more than the analyzed evidence supports.

## Optional references

- `references/data_intake_and_profiling.md`
- `references/analysis_methods.md`
- `references/figure_contract_and_visual_qa.md`
- `references/plotting_principles.md`
- `references/simulation_output_map.md`
- `references/md_structure_analysis.md`
- `references/md_diffusion_transport.md`
- `references/mechanical_elastic_analysis.md`
- `references/electronic_structure_analysis.md`
- `references/phonon_vibrational_analysis.md`
- `references/neb_barrier_analysis.md`
- `references/defect_surface_adsorption_analysis.md`
- `references/mlp_md_analysis_readiness.md`
- `references/community_postprocessing_tools.md`
- `references/tool_specific_visualization_patterns.md`
- `references/tooling_index.md`

Use self-written Python, mature community tools, or project-local scripts as
appropriate. No fixed parser or plotting library is required.
