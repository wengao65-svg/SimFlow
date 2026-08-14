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

- Start with a lightweight Analysis Contract: scientific question, analysis
  object, comparison object, window or transformation, uncertainty approach,
  and intended claim level. Keep it inline for ordinary work unless a separate
  artifact is already useful.
- Define the statistical unit and dependence structure before counting samples
  or estimating uncertainty. Seeds, trajectories, configurations, frames, atoms,
  and time origins are not interchangeable independent replicates.
- Compare runs or models only after checking units, normalization, reference
  zero, selections, sampling conditions, and analysis windows for compatibility.
- Preserve the relationship from raw input through processing to figure data.
- Check units, normalization, sampling, grouping, and missing data before fitting.
- Test plausible windows, cutoffs, bins, smoothing, fit ranges, or normalization
  choices when they could change the conclusion; report material sensitivity.
- Diagnose unexpected results in order: parsing and schema, units and reference
  conventions, calculation failure, analysis artifact, sampling insufficiency,
  model validity, then physical interpretation.
- Distinguish numerical failure, outlier, insufficient sampling, and plausible
  physical behavior.
- Do not edit a figure in a way that changes scientific meaning without a
  reproducible source-data transformation.

## Minimum checks

- Input type, provenance, sample/frame/step count, units, and completeness are
  understood.
- Equilibration and analysis windows are justified.
- Statistical comparisons identify the independent unit, nested or temporal
  dependence, effective sample size or blocking strategy, and uncertainty.
- Cross-run or cross-model comparisons have a documented comparability basis;
  unresolved mismatches remain separate or explicitly conditional.
- The selected visual encoding supports the intended claim.
- Each claim-bearing figure traces to source and derived data, transformations,
  uncertainty choices, the exact supported claim, and explicit non-claims.
- Key numerical values agree across tables, figures, and text.
- Alternative interpretations and evidence limitations are stated.

## Common failure modes

- Plotting before checking units, grouping, or missing frames.
- Inferring convergence from a smooth curve alone.
- Reporting a fitted value without window sensitivity or uncertainty.
- Treating frames, atoms, overlapping time origins, or configurations from one
  correlated trajectory as independent replicates.
- Comparing curves that use different units, reference zeros, normalization,
  sampling conditions, selections, or windows without reconciliation.
- Treating correlation as mechanism or causation.
- Hiding failed runs because they make a figure less clean.
- Using normalization or smoothing that changes the apparent conclusion.
- Explaining an unexpected result physically before excluding parser, unit,
  failed-run, analysis-artifact, sampling, or model-validity causes.
- Treating an attractive figure or caption as evidence for a claim that the
  plotted data and transformation do not support.

## Escalate uncertainty when

- Filtering, fitting, binning, normalization, or uncertainty choices materially
  change the conclusion.
- The statistical unit is ambiguous, dependence is ignored, or effective sample
  size cannot be defended.
- Runs or models are not directly comparable under their current reference,
  unit, sampling, or analysis conventions.
- Outputs are incomplete, unconverged, contradictory, or missing provenance.
- Publication requirements change the supported scientific claim.

## Completion criteria

- The result answers a stated question and remains traceable to source data and
  reproducible processing.
- Statistical independence, comparability, sensitivity, uncertainty, and
  limitations are visible at the level required by the claim.
- Figures and summaries do not claim more than the analyzed evidence supports.
- Final, publication, or handoff figures receive visual QA when useful;
  exploratory analysis does not acquire a mandatory figure-review workflow.

## Optional references

- `references/analysis_rigor_contract.md`
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
- `references/synthetic_analysis_cases.md`

Load references progressively. Start with `analysis_rigor_contract.md`; add
`data_intake_and_profiling.md` for unfamiliar inputs and `analysis_methods.md`
when numerical choices matter. Route MD structure to
`md_structure_analysis.md`, diffusion or transport to
`md_diffusion_transport.md`, electronic structure to
`electronic_structure_analysis.md`, phonons to
`phonon_vibrational_analysis.md`, NEB to `neb_barrier_analysis.md`, and MLP-MD
readiness to `mlp_md_analysis_readiness.md`. Load
`figure_contract_and_visual_qa.md` for final, publication, or handoff figures,
not by default for ordinary exploratory plots.

Use self-written Python, mature community tools, or project-local scripts as
appropriate. No fixed parser or plotting library is required.
