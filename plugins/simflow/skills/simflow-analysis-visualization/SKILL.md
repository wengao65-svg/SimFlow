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

## Output artifacts

- Analysis script, command log, environment note, input data reference, derived data, validation report, and figures or captions.
- Interpretation notes that distinguish measured/calculated results from speculation.
- Figure lineage linking each visual to source data and script artifacts.

## Status write rules

- Register analysis scripts, commands, inputs, outputs, figures, and captions as artifacts under `project_root`.
- Link conclusions to upstream literature, model, computation, derived data, or figure artifacts.
- Record incomplete, missing, unconverged, or suspect outputs explicitly instead of smoothing them into final results.

## Checkpoint rules

- Create a checkpoint when an analysis dataset or figure set is ready for review, handoff, or writing.
- Create a failure checkpoint when parsing, validation, convergence, or reproducibility checks fail.

## Prohibited actions

- Do not fabricate data, plots, convergence status, statistics, or physical interpretation.
- Do not require a fixed parser, plotting library, output schema, report filename, or built-in SimFlow helper.
- Do not hide failed calculations, missing timesteps, failed frames, or statistical uncertainty.

## Manual confirmation scenarios

- Analysis choices materially affect conclusions, such as filtering, fitting, binning, normalization, or uncertainty model.
- Outputs are incomplete, unconverged, contradictory, or inconsistent with the proposed calculation.
- The user needs publication-quality figure conventions or journal-specific formatting.
