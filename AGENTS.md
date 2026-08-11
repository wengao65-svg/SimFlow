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

## Runtime Use

Use runtime only when an event needs inspection, durable recording, approval,
or recovery. Ordinary reading, reasoning, editing, analysis, and writing do not
require a SimFlow state write.

The public state tools are:

- `inspect`: read compact status, records, checkpoints, and legacy migration
  inventory without writing;
- `record`: append one logical milestone, run, deliverable, analysis, approval,
  failure, note, or confirmed migration record;
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
- New state uses `.simflow/project.json`, `.simflow/records.jsonl`,
  `.simflow/checkpoints/`, and `.simflow/reports/`.
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
