---
name: simflow
description: Select at most one computational-research Task Skill and one optional Domain Skill from the user's current intent.
---

# SimFlow Router

## Purpose

`simflow` is a thin intent router. It selects guidance; it does not execute a
workflow, parse scientific files, or own persistence. Selecting a Task or
Domain Skill never requires a state write.

## Use when

- A computational-research request could benefit from one of the bundled Task
  or Domain Skills.
- The current intent has changed and the active guidance should be reconsidered.
- It is unclear whether a request is literature, planning, modeling,
  computation, analysis, or writing.

## Routing model

Research Task Skills answer how to do the current class of work well:

- `simflow-literature-review`
- `simflow-proposal`
- `simflow-modeling`
- `simflow-computation`
- `simflow-analysis-visualization`
- `simflow-writing`

Domain Skills add software- or method-specific knowledge when needed:

- `simflow-vasp`
- `simflow-cp2k`
- `simflow-lammps`
- `simflow-gpumd`
- `simflow-mlp`

## Selection rules

1. Select at most one Research Task Skill from the user's immediate intent.
2. Select at most one Domain Skill when engine- or method-specific knowledge is
   material to the answer.
3. Do not load every Skill that might become relevant later.
4. Skill selection follows current intent, not cwd, directory names, workflow
   stage, or the location of existing files.
5. A request inside a computation directory may need analysis guidance; a
   request inside an analysis directory may need computation guidance.
6. The six recommended research phases are project-organization semantics, not
   mandatory Skill transitions.

## Project memory re-entry

When SimFlow is first used for a project in a user request, the host should call
the read-only `inspect` tool once with `project_root`, `working_directory`, and
the current query. Reuse that result for the rest of the request.

- Do not create session state or a handoff for re-entry.
- Do not repeat `inspect` before every Skill, file read, or tool action.
- Use `selected_experiment_id` silently only when the match is unambiguous.
- If Experiment selection is ambiguous, ask only before a durable Experiment
  write, checkpoint binding, plan binding, transfer, submit, or recorded status.
- Do not print a fixed recovery summary unless it is relevant to the answer.

Examples:

| Current intent | Task Skill | Optional Domain Skill |
| --- | --- | --- |
| analyze GPUMD trajectories | analysis-visualization | gpumd |
| prepare or run VASP NEB | modeling or computation, choose one | vasp |
| design NEP active learning | proposal | mlp |
| train NEP | computation | gpumd |
| compare MACE and NEP | analysis-visualization | mlp |
| draft results from accepted evidence | writing | none |

## Runtime escalation

Runtime is separate from Skill selection. Hand a request to SimFlow runtime
only when an actual event must be inspected, recorded, safeguarded, or
recovered. High-risk events include real local or remote execution, scheduler
submission, credentials, licensed or proprietary files, VASP POTCAR material,
destructive actions, and state recovery.

Experiment notebooks preserve only scientific questions, Attempts,
observations, and decisions. Operational records preserve plan, approval,
transfer, submit, scheduler status, evidence-change, and checkpoint truth.
Actual scientific files remain exact evidence. An Attempt is a scientific
strategy, not an HPC Run, and runtime tools must not create Experiments or
Attempts.

The router identifies the boundary but does not approve, submit, transfer,
record, checkpoint, or recover anything itself.

## Ambiguous intent

- Return the smallest plausible Skill choices and the missing information.
- Ask only when the ambiguity blocks useful or safe progress.
- Do not default unknown software to a supported engine.
- Do not default an unknown computation to static, ENERGY, NVT, or training.
- If no bundled Domain Skill applies, use the relevant Task Skill alone and
  preserve the unknown tool as context.

## Prohibited actions

- Do not act as a centralized workflow executor, domain parser, submitter, or
  approval gate.
- Do not require MCP engagement merely because a Skill was selected.
- Do not turn the one read-only project-memory inspection into a session or
  activity lifecycle.
- Do not choose Skills from the current phase or directory name.
- Do not fabricate literature, inputs, outputs, figures, citations,
  convergence, approval, or job states.
- Do not duplicate software capability claims; use the shared toolchain
  contract when capability detail is needed.

## Completion criteria

- Zero or one Task Skill is selected.
- Zero or one Domain Skill is selected.
- Any runtime escalation is stated separately from Skill guidance.
- Existing Experiment context was inspected at most once for this project in
  the current user request when SimFlow runtime was used.
- Unknown intent or unsupported tools are not silently mapped to known paths.
