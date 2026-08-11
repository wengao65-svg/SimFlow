---
name: simflow
description: Select at most one computational-research Task Skill and one optional Domain Skill from the user's current intent.
---

# SimFlow Router

## Purpose

`simflow` is a thin intent router. It selects guidance; it does not execute a
workflow, parse scientific files, manage persistence, or require state calls.

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
- Do not choose Skills from the current phase or directory name.
- Do not fabricate literature, inputs, outputs, figures, citations,
  convergence, approval, or job states.
- Do not duplicate software capability claims; use the shared toolchain
  contract when capability detail is needed.

## Completion criteria

- Zero or one Task Skill is selected.
- Zero or one Domain Skill is selected.
- Any runtime escalation is stated separately from Skill guidance.
- Unknown intent or unsupported tools are not silently mapped to known paths.
