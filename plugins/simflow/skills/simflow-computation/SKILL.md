---
name: simflow-computation
description: Guide disciplined preparation, validation, diagnostic execution, monitoring, and interpretation boundaries for scientific computations.
---

# Scientific Computation

## Purpose

Provide general execution discipline for computational research without owning
submission plumbing, approval policy, job registries, or workflow state.

## Use when

- Preparing, validating, smoke-testing, running, resuming, or diagnosing a
  scientific calculation.
- Reviewing whether an existing calculation is ready for expensive execution.
- Determining whether a run actually completed and produced usable evidence.

## Do not use when

- The task is only scientific model construction, output analysis, or writing.
- The user only needs software-specific syntax; pair with one Domain Skill
  rather than loading several Task Skills.

## Task principles

- Inspect existing inputs and validated project conventions before changing
  anything.
- Confirm that the software, method, model, and requested observable agree.
- Prefer static checks and a small diagnostic run before costly production work.
- Preserve user parameters unless a change is scientifically justified and
  disclosed.
- Distinguish prepared, submitted, queued, running, exited, numerically
  converged, and scientifically usable states.
- Treat scheduler submission as evidence of submission only.
- Diagnose failures before retrying; do not silently relax scientific settings.
- Resume from trustworthy software restart data when possible.

## Minimum checks

- Required inputs, referenced files, executables, versions, and units are known.
- Syntax and cheap consistency checks pass.
- Resource scale and expected outputs are plausible.
- A diagnostic or dry-run path exists before production execution.
- Exit status, completion markers, numerical convergence, and critical warnings
  are inspected after execution.
- The calculation has not been called successful merely because files exist or
  a parser can read them.

## Common failure modes

- Equating a job ID with successful computation.
- Equating a normal process exit with numerical or scientific convergence.
- Overwriting a successful reference run during troubleshooting.
- Changing cutoffs, tolerances, timestep, model, or ensemble without disclosure.
- Repeating an expensive run before identifying the failure mode.
- Inventing missing outputs or treating partial output as final evidence.

## Escalate uncertainty when

- Real local, remote, or HPC execution is requested.
- Credentials, licensed files, proprietary inputs, destructive actions, or high
  resource cost are involved.
- A parameter change could alter the scientific interpretation.
- Output is incomplete, contradictory, or insufficient to determine convergence.

## Completion criteria

- Preparation, execution state, and scientific usability are distinguished.
- Validation evidence and unresolved warnings are reported.
- No stronger completion claim is made than the observed outputs support.

## Optional references

Pair with at most one relevant Domain Skill for software-specific input,
restart, convergence, and output semantics. Runtime safety and event recording
remain separate from this guidance.
