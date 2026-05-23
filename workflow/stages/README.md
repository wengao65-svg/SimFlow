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

The following files are legacy aliases or compatibility activities:

- `literature` maps to `literature_review`
- `review` maps to `literature_review` or cross-stage review activity
- `input_generation` maps to an optional activity inside `computation`
- `compute` maps to `computation`
- `analysis` maps to `analysis_visualization`
- `visualization` maps to `analysis_visualization`

Keep aliases loadable for old projects and tests, but do not treat them as the
canonical stage vocabulary for new workflow-layer work.
