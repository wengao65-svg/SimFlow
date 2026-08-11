# SimFlow User Guide

## Choose Guidance From Intent

Use `simflow` as a thin router or select a specific Skill. One task should load
at most one Research Task Skill and one optional Domain Skill.

Examples:

| Intent | Task Skill | Domain Skill |
| --- | --- | --- |
| analyze GPUMD trajectories | analysis/visualization | GPUMD |
| prepare VASP NEB inputs | modeling or computation, choose one | VASP |
| design NEP active learning | proposal | MLP |
| write accepted results | writing | none |

Skills follow current intent, not cwd or phase. They can guide useful work when
SimFlow MCP is unavailable.

## When To Use Runtime

Use runtime only when you need to:

- inspect durable project state or recovery points;
- record one meaningful milestone, run, deliverable, analysis, approval, or
  failure;
- create or validate a real recovery reference;
- plan, transfer, submit, or monitor real execution;
- explicitly index legacy SimFlow state.

Ordinary reading, editing, plotting, literature synthesis, and draft writing do
not need a state call merely because a Skill was used.

## Re-enter An Existing Project

1. Inspect the project root and existing layout.
2. On the first SimFlow use for this project in the current user request, call
   `simflow_state/inspect` once with `working_directory` and the current query.
3. Reuse that result for the request; do not inspect before every Skill or file
   action.
4. Continue from exact files and the selected Experiment when the match is
   unambiguous. Ask before a durable binding when selection is ambiguous.
5. Record only new scientific memory or operational events that need durable
   provenance.
6. Create a checkpoint only when restart references or a meaningful diagnostic
   boundary exist.

The compact summary exposes active Experiments, current goal, active run,
recent milestone, failure, checkpoint, open material actions, and next action.
No session, iteration, activity, or mandatory handoff lifecycle is required.

## Experiment Memory

Use `record(channel="experiment")` for durable scientific semantics that a
later request must recover: the scientific question, Attempts, observations,
decisions, material evidence changes, recovery choices, uncertainty, and next
action. Do not mirror raw trajectories, structures, outputs, or logs into the
notebook; those files remain exact evidence and are referenced by path/hash.

An Experiment follows one scientific question. Parameter variants such as
temperature, element, seed, retry, and resume are Attempts unless they change
the question or acceptance criteria. Ordinary parameter edits are Attempts or
Decisions. Use `material_action` only for persistent changes to evidence or
recoverability, and record both the planned action and terminal outcome.

## Records

Use one record for a logical deliverable or run. A directory of outputs may be
represented by a manifest or a few key file references. Parent record IDs can
link an analysis to its run or a figure to its processed data.

Do not record temporary files, repeated copies, helper invocation receipts, or
reports whose only purpose is to prove that another record exists.

## Stages And Recipes

The six stage names provide shared research vocabulary. They do not require
ordered transitions. DFT, AIMD, classical MD, MLP-MD, phonon, NEB, and custom
paths are recipes or tags, not fixed executor DAGs.

Project directories are independent of runtime stages. SimFlow respects an
existing layout and offers the six `phaseN_*` directories only as a template
for new work.

## Computation And HPC

Before real local, remote, or scheduler execution:

1. inspect existing inputs and preserve validated scientific parameters;
2. run cheap validation or a smoke test where appropriate;
3. call `hpc/plan` with the exact script and inputs;
4. review the returned validation, credential scan, restricted files, target,
   resources, and `run_plan_hash`;
5. record explicit user approval bound to that hash;
6. use `hpc/transfer` when the plan declares remote transfer;
7. call `hpc/submit` with the same hash and approval reference;
8. use `hpc/status` for scheduler state and inspect scientific outputs
   separately.

Changing the script, inputs, target, remote directory, resources, transfer
scope, destructive scope, or restricted-file metadata invalidates approval.
An unchanged retry or resume can reuse it.

A scheduler job ID means submission occurred; it does not mean the calculation
completed. Output existence does not prove convergence, and parser success does
not prove scientific validity.

Production or scientific readiness decisions are not submit decisions. A
production-readiness result still requires separate `hpc_submit` evidence,
approval bound to the current run plan, and a real submit record.

## POTCAR

VASP POTCAR may be materialized from a user-owned licensed library into a
controlled calculation directory. Variant selection must be exact. SimFlow may
record element, dataset, relative path, size, hash, and validation metadata.
POTCAR content must never enter `.simflow`, Git, logs, checkpoints, packages,
or MCP responses.

## Analysis And Figures

Choose the analysis location from the actual input scope:

- one calculation unit: near that unit;
- multiple runs in one stage: one stage-level analysis entry;
- multiple stages in one phase: the meaningful phase common parent;
- only project-wide synthesis: phase 5 when that template is used.

Keep one authoritative location. Use shallow README indexes and relative links
instead of copying or symlinking results. Record analysis only at logical
deliverable granularity, including relevant inputs, script/environment, main
outputs, uncertainty, and parent record IDs.

## Writing

Claims must remain traceable to real evidence. Do not turn a trend into a
mechanism, correlation into causation, a planned calculation into a result, or
an unfinished run into completed evidence. Methods must describe what was
actually executed.

## Legacy Migration

`inspect` reports legacy `.simflow/state/*.json`, old `.simflow/memory/` files,
and nested `.simflow` roots without writing. Memory inventory includes only
path, size, hash, safe JSON shape, and SQLite header metadata; it never queries
SQLite tables or imports memory content. To persist a compact index, use the
operational `record(kind="migration")` branch with `confirm_migration=true` and
the exact current report hash. The operation does not reorganize the project
or import host conversations.
