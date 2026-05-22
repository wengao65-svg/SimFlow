# SimFlow Agent Guidelines

## Identity

You are operating within the SimFlow Domain Workflow Layer — a Codex-native plugin for computational simulation research workflows.

SimFlow is a workflow layer, not a workflow executor. Codex, Claude Code, or the host agent remains responsible for scientific reasoning, literature search, modeling, coding, analysis, and writing. SimFlow provides research-stage semantics, state, artifact lineage, checkpoints, safety gates, and handoff discipline.

## Core Principles

1. **Skill-first**: All user interactions enter through skills. Never bypass the skill layer.
2. **Workflow-layer driven**: Use declared stages, recipes, gates, and policies as research contracts, not as a centralized executor.
3. **State-aware**: Always read `.simflow/state/` before acting. Always write state after changes.
4. **Artifact-tracked**: Every output must be registered as an artifact with metadata and lineage.
5. **Checkpoint-resilient**: Create checkpoints at stage boundaries. Support recovery from any checkpoint.
6. **Dry-run first**: All compute operations default to dry-run. Real HPC submission requires explicit approval.
7. **No LLM implementation**: SimFlow does not implement or configure LLM models. The host (Codex/OMX) handles inference.

## State Boundary

- `.simflow/` is the only SimFlow workflow state root.
- `plugin_root` is only for importing SimFlow code and bundled assets. `project_root` is the user's current project directory and is the only valid write root for `.simflow/`, reports, artifacts, and checkpoints.
- MCP servers commonly run with cwd set to the plugin root/cache. SimFlow tools must not infer the user project from MCP cwd; callers must pass `project_root`.
- `.omx/` belongs to oh-my-codex / host session state. SimFlow may read it for host context, but must not use it as the workflow state root.
- `$simflow` project initialization must call `simflow_state.init_workflow`, which creates `.simflow/state/workflow.json`, `.simflow/state/stages.json`, `.simflow/state/artifacts.json`, `.simflow/state/checkpoints.json`, and the `.simflow/artifacts`, `.simflow/checkpoints`, `.simflow/reports`, and `.simflow/logs` directories.
- SimFlow status summaries belong under `.simflow/reports/status_summary.md` or `.simflow/state/summary.json`, never under `.omx/`.
- Existing `.omx/` content must not be deleted or modified by SimFlow initialization.
- Any skill that writes reports, artifacts, checkpoints, or state must first resolve `pwd` as `project_root`, ensure/init the `.simflow/` tree there, and then write under that project root.

## Stage And Recipe Rules

- Default top-level stages are `literature_review`, `proposal`, `modeling`, `computation`, `analysis_visualization`, and `writing`.
- DFT, AIMD, classical MD, phonon, NEB, defect, adsorption, and custom paths are recipes or tags, not top-level workflow restrictions.
- Each stage must verify the evidence needed for its current research intent before completion.
- Each completed stage boundary must produce at least one registered artifact and a checkpoint.
- Stage transitions that involve risky actions must pass the declared verification or approval gate.
- The `computation` stage requires dry-run evidence before real local, remote, or HPC execution.
- Any stage can be entered independently if its inputs and evidence requirements are satisfied.
- `input_generation` is an optional activity inside `computation`; `visualization` is an optional activity inside `analysis_visualization`; review is a cross-stage checking action.

## Prohibited Actions

- Never submit HPC jobs without passing the approval gate.
- Never run real local or remote compute jobs without the same approval discipline used for HPC jobs.
- Never store credentials in the repository, artifacts, or logs.
- Never skip verification gates.
- Never write artifacts without metadata.
- Never create checkpoints without workflow/stage/job association.
- Never implement LLM model calls or configuration.
- Never act as a CLI entry point — SimFlow is skill-driven only.
- Never record an unfinished calculation as a completed result.
- Never fabricate literature, data, figures, citations, or scientific claims.

## Error Handling

- On failure: create a failure checkpoint, write an error report, and notify the user.
- On verification failure: do not proceed to the next stage. Report what failed and why.
- On missing inputs: report which inputs are missing and suggest how to obtain them.

## Handoff Protocol

When handing off to another agent or ending a session:
1. Summarize the current workflow state.
2. List all produced artifacts.
3. Note the latest checkpoint.
4. Highlight any risks or warnings.
5. Suggest the next steps.
6. Indicate whether user approval is needed.
