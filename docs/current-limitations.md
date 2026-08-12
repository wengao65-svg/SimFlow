# Current Product Limitations

This page describes the current release boundary. Review it before publishing
release notes or marketplace packages.

## Supported Domain Skills

The public product includes Domain Skills for:

- VASP;
- CP2K;
- LAMMPS;
- GPUMD/NEP;
- engine-independent MLP methodology.

These Skills provide scientific guidance and may use optional validation,
generation, parsing, or analysis helpers. They do not own runtime state or make
SimFlow a workflow executor.

GPUMD and NEP have bounded helper support for input preparation, static
validation, dry-run planning, selected output parsing, orchestration metadata,
and evidence handoff. SimFlow does not claim an engine-specific GPUMD/NEP real
execution implementation. A user-provided script may still use the generic,
approval-bound HPC runtime.

`workflow/toolchains/capabilities.json` describes helper support. Optional
helper output does not establish that a calculation completed or that a result
is scientifically valid.

## Unsupported Engines

Unsupported engines do not receive placeholder Skills. The router keeps the
requested software as context, selects the relevant Research Task Skill, and
states uncertainty instead of mapping the request to a supported engine.

QE, Gaussian, ABINIT, GROMACS, OpenMM, Phonopy, NEPTrainKit, DeePMD, MACE,
NequIP, Allegro, and other tools may appear in project records or user-provided
scripts. SimFlow does not advertise engine-specific generation, validation,
parsing, execution, or scientific interpretation for them unless a tested
Domain Skill and release contract exist.

## Runtime Observation Boundary

SimFlow records only events that pass through its compact runtime. It does not
observe arbitrary host shell commands, parse Codex/Claude/OpenCode transcripts,
or infer that a Skill was loaded.

New state consists of append-only `.simflow/experiments/*.md` notebooks,
`.simflow/records.jsonl`, compact checkpoints, reports, and deterministic
`project.json`/Experiment-index views. Historical `.simflow/state/*.json`,
legacy `.simflow/memory/`, and nested `.simflow` roots are read-only
compatibility input. Explicit migration writes a single metadata index and
never reorganizes or imports source content.

There is no SQLite/session/activity ledger, Experiment lifecycle controller,
per-file artifact registry, automatic session handoff, or automatic stage
checkpoint. Compact Experiment notebooks are intentionally retained to prevent
loss of scientific questions, Attempts, observations, decisions, and next steps
across host sessions. Their ontology is capped at those four entry types.
Persistent evidence changes and technical recovery remain operational facts,
not notebook lifecycles.

## Execution Boundary

The public HPC surface is `plan`, `transfer`, `submit`, and `status`. Real
local, remote, or scheduler execution requires:

- a current immutable run plan;
- dry-run validation and credential scan from that plan;
- explicit approval bound to its exact `run_plan_hash`;
- unchanged script, inputs, target, resources, transfer scope, destructive
  scope, and restricted-file metadata.

Remote file movement uses `hpc/transfer` with `direction=upload|download` and a
verified manifest. SSH operations use the isolated credential broker. Direct
host `ssh` or `scp` commands are outside SimFlow's observable runtime and must
not be represented as tracked SimFlow execution.

An unchanged retry may reuse approval. A materially changed plan requires new
approval. Job submission, output existence, and parser success do not prove
scientific completion.

## Licensed And Large Scientific Artifacts

The repository and generated distributions must not contain real VASP
`POTCAR`, `WAVECAR`, `CHGCAR`, `OUTCAR`, or `vasprun.xml` artifacts. Examples may
include redistributable metadata placeholders or explicit synthetic fixtures.

A user-owned POTCAR library may be materialized into a controlled calculation
directory and transferred through an approved run plan. POTCAR bodies remain
outside `.simflow`, Git, packages, checkpoints, logs, and ordinary records.

## Distribution Boundary

Codex and Claude marketplace branches and the `opencode-simflow` npm package
are the user-facing distribution channels. The OpenCode adapter targets stable
OpenCode `1.18.9 <= version < 2`; V2 beta APIs are outside the current contract.
PyPI is not the primary install path until a package is published and
install-smoked.

Standard MCP `clientInfo` may tailor discovery wording. It does not change tool
semantics, approval, project-root checks, or credential isolation.

## Scientific Responsibility

Research Task and Domain Skills improve how work is performed. The host agent
and user remain responsible for scientific decisions, literature selection,
model choices, parameter justification, interpretation, and final claims.
SimFlow must not turn planned, submitted, partial, parsed, or failed work into a
completed scientific result.
