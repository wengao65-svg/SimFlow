# Skills Directory

SimFlow exposes exactly 12 public Skills. They provide reusable scientific
guidance and do not own runtime state, persistence, approval, or recovery.

## Router

- `simflow`: selects at most one Research Task Skill and one optional Domain
  Skill from the user's current intent.

## Research Task Skills

- `simflow-literature-review`
- `simflow-proposal`
- `simflow-modeling`
- `simflow-computation`
- `simflow-analysis-visualization`
- `simflow-writing`

These are pure instruction bundles. They guide how to perform a class of
research work, which checks matter, where agents commonly fail, when
uncertainty must be escalated, and when the task is complete. They must not
require MCP calls, advance workflow stages, register artifacts, create
checkpoints, enforce project directories, or decide runtime approval.

## Domain Skills

- `simflow-vasp`
- `simflow-cp2k`
- `simflow-lammps`
- `simflow-gpumd`
- `simflow-mlp`

Domain Skills add engine- or method-specific knowledge to the current Task
Skill. They may ship references and optional bounded helper scripts, but they
do not own workflow progression or runtime state.

QE, Gaussian, and other unsupported tools do not receive placeholder Skills.
The router keeps them as unknown context and uses the relevant Task Skill
without claiming built-in engine support.

## Loading Rule

One ordinary request should select no more than:

```text
one Research Task Skill + one optional Domain Skill
```

Skill selection follows current intent, not cwd, phase, or directory names.
Safety policy, event recording, checkpointing, recovery, verification of actual
execution, and handoff serialization belong to SimFlow runtime.

## Script Boundary

Task and Domain helpers must remain useful without SimFlow MCP. A helper may
inspect, parse, validate, or prepare files through host tools. Optional runtime
recording must not be required for the helper's scientific function.

Property analysis and figure construction belong to the analysis Task Skill.
Domain helpers may parse software-specific output semantics but should not
silently choose final fit windows, statistics, or scientific claims.
