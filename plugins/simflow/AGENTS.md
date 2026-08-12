# SimFlow Agent Guidelines

## Identity

SimFlow is a computational-research guidance, provenance, recovery, and safety
layer. It is not a workflow executor. The host agent remains responsible for
scientific reasoning, literature work, modeling, coding, analysis, and writing.

## Architecture Boundaries

SimFlow separates four concerns:

1. The router selects at most one Research Task Skill and one optional Domain
   Skill from the user's current intent.
2. Research Task Skills guide literature review, proposal, modeling,
   computation, analysis/visualization, or writing.
3. Domain Skills add VASP, CP2K, LAMMPS, GPUMD/NEP, or general MLP knowledge.
4. Runtime records and safeguards events that actually happened.

Task and Domain Skills are pure guidance. They must not require state calls,
own stage transitions, create checkpoints as completion conditions, enforce a
directory layout, or decide that real execution was approved or successful.

## Memory Re-entry

Experiment memory is a host/runtime concern, not a Task or Domain Skill
lifecycle. On the first SimFlow use for a project in each user request:

1. call `inspect` once with explicit `project_root`, the current working
   directory, and a concise form of the user's current request;
2. reuse that result for the remainder of the request rather than repeatedly
   reading state before each action;
3. silently continue with a selected Experiment only when `inspect` returns one
   unambiguous match;
4. ask before a durable write or execution binding when multiple Experiments
   remain plausible;
5. do not create a session record, handoff, checkpoint, or fixed user-facing
   summary merely because re-entry occurred.

This read is optional when SimFlow is not being used. It is always read-only and
must not initialize `.simflow`.

## Runtime Use

Use runtime only when an event needs inspection, durable recording, approval,
or recovery. Ordinary reading, reasoning, editing, analysis, and writing do not
require a SimFlow state write.

The public state tools are:

- `inspect`: read relevant Experiment memory, operational status, recovery
  points, and legacy migration inventory without writing;
- `record`: append either one operational record or one schema-discriminated
  Experiment notebook entry;
- `checkpoint`: create a compact recovery reference;
- `recover`: validate recovery references without executing compute or rolling
  back project files.

The public HPC tools are `plan`, `transfer`, `submit`, and `status`. Real local,
remote, or scheduler execution requires an immutable `run_plan_hash` and an
approval record bound to that exact hash. An unchanged retry may reuse the same
approval. Any change to script, inputs, target, remote directory, resources,
transfer scope, destructive scope, or restricted-file metadata invalidates it.

## State Boundary

- `.simflow/` is the only SimFlow runtime root and belongs at explicit
  `project_root`.
- New state uses `.simflow/experiments/`, `.simflow/project.json`,
  `.simflow/records.jsonl`, `.simflow/checkpoints/`, and `.simflow/reports/`.
- Experiment notebooks own scientific semantics. `records.jsonl` owns
  operational execution truth. Actual project files remain exact evidence.
- Legacy `.simflow/state/*.json` and nested `.simflow` roots are read-only
  compatibility inputs. Never rewrite or relocate them automatically.
- `inspect` is read-only and must not initialize a project.
- `record` or `checkpoint` may create only the compact paths needed for that
  operation.
- MCP servers run from the plugin installation, so every project operation must
  receive `project_root`; never infer it from MCP cwd.
- `.omx/` and other host-session stores are not SimFlow state. Do not import
  host transcripts into SimFlow migration or provenance.
- A migration requires the current `migration_report_hash` and explicit
  `confirm_migration=true`. Migration creates an index/report only; it does not
  move, rename, delete, or rewrite scientific files.

## Recording And Recovery

- Record logical runs, milestones, deliverables, analyses, approvals, and
  failures once. Do not register every intermediate file or helper action.
- Define an Experiment by its scientific question. Temperature, element, seed,
  retry, and resume variants are Attempts unless the question or acceptance
  criteria change.
- Experiment notebooks have a fixed four-entry ontology: Experiment states the
  question, Attempt states a scientific strategy, Observation states what was
  seen, and Decision states what follows. Do not add lifecycle entry types.
- Record a completed, partial, or failed persistent evidence change as one
  immutable `evidence_change` operational event. It is never a lifecycle
  controller; plans belong to approval or run-plan records, and a later undo is
  a new event linked with `parent_ids`.
- An Attempt is a scientific strategy and may reference multiple operational
  Runs. A Run is one actual execution. HPC may bind existing Experiment and
  Attempt IDs but must never create either entity.
- Use file references, hashes, manifests, and `parent_ids` to preserve useful
  provenance without duplicating registries.
- A scheduler job ID means submitted, not completed. A readable output means
  present, not converged or scientifically trustworthy.
- Create a checkpoint only when there is real recovery value: a run or
  milestone reference, input/restart hashes, restart paths, a resume command,
  or diagnostic risk notes.
- Ordinary task or stage completion does not require a checkpoint.
- Recovery validates references and hashes. It never restores legacy state
  snapshots or silently changes project files.
- Experiment and Attempt IDs are operational binding metadata and never enter
  `run_plan_hash` or invalidate approval for an otherwise unchanged plan.

## Project Organization

SimFlow respects the existing project layout. The six phase directories are a
recommended template for new projects, not a runtime requirement:

```text
phase1_literature_review/
phase2_proposal/
phase3_modeling/
phase4_computation/
phase5_analysis_visualization/
phase6_writing/
```

Do not move or rename existing project content merely to match this template.
Directory diagnostics are advisory and must not block scientific work.

Place analysis according to the inputs it consumes:

- one calculation unit: near that unit;
- multiple runs in one stage: one stage-level analysis entry;
- multiple stages in one phase: the meaningful phase-level common parent;
- project-wide synthesis only: `phase5_analysis_visualization/` when that
  template exists.

Use one authoritative result location and shallow relative-link indexes. Do
not copy or symlink results to manufacture a second source of truth.

## Safety Boundaries

- Never execute a real local, remote, or scheduler job without approval bound
  to the current immutable run plan.
- Never treat submission, file existence, parser success, or a directory name
  as scientific completion or approval.
- Never store credentials, passwords, tokens, private keys, key paths, or
  arbitrary SSH options in records, reports, logs, or generated files.
- POTCAR may be materialized only from a user-owned licensed library into a
  controlled calculation directory. Persist metadata only; never return,
  record, commit, package, checkpoint, or redistribute POTCAR content.
- Never fabricate literature, citations, data, figures, convergence, job
  status, or scientific claims.
- Never silently change validated scientific parameters.
- Never auto-migrate or restructure user data.
- SimFlow does not implement or configure LLM inference.

## Failures And Handoff

On failure, preserve the real status and the evidence needed to diagnose it.
Record a failure only when durable project history is useful. Create a
checkpoint only if recovery references exist or a diagnostic boundary is
valuable.

A host handoff should summarize the current goal, active or recent runs,
meaningful deliverables, latest recoverable checkpoint, risks, next action, and
approval needs. A handoff summary is not a mandatory runtime write.
