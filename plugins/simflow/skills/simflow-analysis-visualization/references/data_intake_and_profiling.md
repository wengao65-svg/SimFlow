# Data Intake And Profiling

Use this reference before selecting a parser, plotting library, chart type,
fitting method, or visual style. The goal is to understand the evidence surface
first so plots and statistics do not outrun the data.

## Intake record

- Record the project root, source directory, input paths, parent artifact ids
  when available, software provenance, run type, and whether each file is raw
  output, user-edited data, or derived data.
- Preserve raw outputs. Write parsed tables, cleaned tables, summaries, and
  figures as separate artifacts with lineage back to the source files.
- Record missing predecessors such as topology files, restart files, charge
  density files, frame metadata, line-mode paths, model identifiers, or scripts
  used to create user-provided tables.
- Treat unknown CSV, JSON, HDF5, text tables, and trajectories as generic inputs
  until the schema and units are understood.

## Profiling checklist

- Identify columns, arrays, frames, timesteps, atom counts, sample counts,
  grouping variables, categorical labels, and coordinate or cell metadata.
- Record units and unit conversions. If units are unknown, keep the result in a
  review or exploratory state and avoid final-result language.
- Check missing values, nonnumeric tokens, duplicate records, nonmonotonic
  timesteps, skipped frames, changed atom counts, empty groups, and obvious
  outliers before fitting or plotting.
- For grouped data, record per-group sample size and whether groups represent
  independent calculations, frames from one trajectory, spatial bins, repeated
  seeds, or user-defined categories.
- For trajectory data, record topology source, atom identity, periodic boundary
  handling, timestep, frame count, equilibration cut, production window, and
  whether coordinates are wrapped or unwrapped.

## Readiness decisions

- Choose chart type from the scientific question plus the profiled data shape:
  trend, distribution, comparison, correlation, composition, spatial structure,
  spectrum, or trajectory-derived metric.
- If the data are too sparse, unbalanced, incomplete, or ambiguous for the
  requested plot, state the limitation and recommend a review plot, table, or
  additional parsing step instead of forcing a publication figure.
- If filtering, binning, smoothing, normalization, fitting windows, or
  equilibration cuts can change the conclusion, route to
  `analysis_methods.md` and record the chosen values and rejected alternatives.
- If the deliverable is a figure for writing or handoff, route to
  `figure_contract_and_visual_qa.md` before rendering final outputs.

## Minimal profile artifact

A useful profile artifact should include:

- source paths and parent artifact ids
- software or data provenance
- raw vs derived classification
- schema or column/array interpretation
- units and conversion assumptions
- sample, group, frame, or step counts
- missing, skipped, warning, or suspect states
- recommended analysis or visualization routes

Do not treat the profile as a scientific result by itself. It is an evidence
map that helps the agent choose a traceable analysis path.
