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

Historical names may still appear in old project records or user language, but
the runtime no longer loads them as stage aliases:

- `literature` maps to `literature_review`
- `review` maps to `literature_review` or cross-stage review activity
- `input_generation` maps to an optional activity inside `computation`
- `compute` maps to `computation`
- `analysis` maps to `analysis_visualization`
- `visualization` maps to `analysis_visualization`

Treat those names only as activity labels or migration input. New workflow-layer
work should use only the canonical stage definition files in this directory.
