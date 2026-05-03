# SimFlow Agent Guidelines

## Identity

You are operating within the SimFlow Domain Workflow Layer — a Codex-native plugin for computational simulation research workflows.

## Core Principles

1. **Skill-first**: All user interactions enter through skills. Never bypass the skill layer.
2. **Workflow-driven**: Follow the declared workflow stages, gates, and policies.
3. **State-aware**: Always read `.simflow/state/` before acting. Always write state after changes.
4. **Artifact-tracked**: Every output must be registered as an artifact with metadata and lineage.
5. **Checkpoint-resilient**: Create checkpoints at stage boundaries. Support recovery from any checkpoint.
6. **Dry-run first**: All compute operations default to dry-run. Real HPC submission requires explicit approval.
7. **No LLM implementation**: SimFlow does not implement or configure LLM models. The host (Codex/OMX) handles inference.

## Stage Progression Rules

- Each stage must verify its required inputs before execution.
- Each stage must produce at least one artifact.
- Each stage must create a checkpoint upon completion.
- Stage transitions must pass through the declared verification gate.
- The `compute` stage requires explicit user approval for real HPC submission.
- Any stage can be entered independently if its inputs are satisfied.

## Prohibited Actions

- Never submit HPC jobs without passing the approval gate.
- Never store credentials in the repository, artifacts, or logs.
- Never skip verification gates.
- Never write artifacts without metadata.
- Never create checkpoints without workflow/stage/job association.
- Never implement LLM model calls or configuration.
- Never act as a CLI entry point — SimFlow is skill-driven only.

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
