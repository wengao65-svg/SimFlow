---
name: simflow
description: Apply SimFlow-wide provenance, project-memory re-entry, durable recording, recovery, and execution-safety semantics when the user explicitly invokes SimFlow. Does not select or route other Skills.
disable-model-invocation: true
---

# SimFlow Framework

## Purpose

`simflow` is an opt-in Framework Skill. It applies SimFlow-wide provenance,
project-memory, recording, recovery, and execution-safety semantics to the
current request. It is not a Skill router, workflow executor, or scientific
reasoner.

## Skill discovery and composition

The host agent owns discovery and composition of Research Task, Domain, and
host-native custom Skills.

- Use Skill names and descriptions for host-native progressive disclosure.
- Load the smallest set of Skills that materially improves the current request;
  this is a context-efficiency principle, not a numeric cardinality rule.
- Multiple Research Task or Domain Skills may be combined when the work spans
  their responsibilities.
- Respect Skills explicitly selected by the user.
- Do not preload Skills merely because they may become useful later.
- Resolve overlapping guidance by responsibility and specificity. No Skill may
  weaken runtime safety, provenance, or scientific-truthfulness requirements.
- Surface a material unresolved conflict instead of inventing a central routing
  decision.

SimFlow does not maintain an intent map, select other Skills, emit a router
result, or manage a custom-Skill registry. Host-native custom Skills may
participate without becoming SimFlow runtime state.

## Project memory re-entry

Use project memory only when the current request depends on existing SimFlow
project truth, prior Experiment context, recovery state, or a durable runtime
action.

When re-entry is needed:

- Call read-only `inspect` once with the available project root, working
  directory, and current query.
- Reuse that result for the current request.
- Do not create session or activity state for re-entry.
- Use an unambiguous Experiment match silently.
- Resolve ambiguity only when it would affect a durable write, checkpoint,
  plan, transfer, submit, or recorded status.
- Do not inspect merely because a SimFlow Skill is active.
- Do not print a fixed recovery summary unless it is relevant to the request.

## Runtime use

Use runtime only when an event needs inspection, durable recording, approval,
or recovery. Ordinary reading, reasoning, editing, analysis, plotting, and
writing do not require a state write.

- `inspect` reads project truth and recovery context without writing.
- `record` appends one meaningful operational fact or Experiment entry.
- `checkpoint` creates a compact recovery reference when restart value exists.
- `recover` validates recovery references without executing compute or rolling
  back project files.
- `plan`, `transfer`, `submit`, and `status` provide the bounded HPC surface.

Actual scientific files remain exact evidence. Experiment notebooks own
scientific questions, Attempts, observations, and decisions. Operational
records own execution and evidence-change truth.

## Provenance and recovery semantics

- Record logical runs, milestones, analyses, deliverables, approvals, and
  failures once; do not register every intermediate file or helper action.
- Treat a scheduler job ID as submitted, not completed, and readable output as
  present, not converged or scientifically trustworthy.
- Create checkpoints only when restart paths, hashes, commands, or diagnostic
  boundaries provide real recovery value.
- Preserve file references, hashes, manifests, and parent links without copying
  scientific evidence into SimFlow state.
- Keep Experiment and Attempt identity separate from immutable execution-plan
  identity.

## Safety semantics

- Never execute a real local, remote, or scheduler job without approval bound
  to the current immutable run plan.
- Never store credentials, tokens, passwords, private keys, key paths, or
  arbitrary SSH options in records or generated files.
- Keep licensed POTCAR content out of responses, state, checkpoints, packages,
  and version control; persist metadata only.
- Never fabricate literature, data, figures, convergence, approval, or job
  status.
- Never silently change validated scientific parameters, migrate user data, or
  reorganize the project layout.

## Prohibited actions

- Do not route or select Research Task, Domain, or custom Skills.
- Do not impose Skill cardinality limits or a static intent-to-Skill mapping.
- Do not require runtime engagement merely because a Skill was loaded.
- Do not turn memory inspection into a session lifecycle.
- Do not approve, submit, transfer, checkpoint, or record events that did not
  actually occur.

## Completion criteria

- Framework semantics were applied only because the user explicitly opted in.
- Any relevant Skills were discovered and composed by the host, not by SimFlow.
- Project memory was inspected at most once and only when the request depended
  on existing project truth, recovery, or a durable action.
- Durable events, recovery references, and execution approvals reflect what
  actually happened.
- Runtime safety and scientific-truthfulness boundaries remain intact.
