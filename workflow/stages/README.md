# Workflow Stages

Stage definitions describe research intent, evidence boundaries, and handoff
contracts. They are not executor nodes and they do not force a centralized DAG.
The host agent remains responsible for scientific reasoning, tool choice,
coding, analysis, and writing.

The canonical workflow-layer stages are:

- `literature_review`
- `proposal`
- `modeling`
- `computation`
- `analysis_visualization`
- `writing`

These stages can be entered independently when their inputs and evidence needs
are satisfied. Stage boundaries should be recorded through `.simflow/` state,
artifacts, checkpoints, lineage, gate evidence, and handoff notes.

The runtime keeps the following legacy aliases loadable through code-level
mapping for old projects and user input:

- `literature` maps to `literature_review`
- `review` maps to `literature_review` or cross-stage review activity
- `input_generation` maps to an optional activity inside `computation`
- `compute` maps to `computation`
- `analysis` maps to `analysis_visualization`
- `visualization` maps to `analysis_visualization`

Do not add bundled alias JSON files for these names. New workflow-layer work
should use only the canonical stage definition files in this directory.
