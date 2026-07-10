# Current Product Limitations

This page describes the current release boundary. It should be reviewed before
publishing release notes or marketplace branches.

## Supported Domain Assistants

The current product build includes Domain Assistants for:

- VASP
- CP2K
- LAMMPS
- GPUMD/NEP input generation, validation, dry-run planning, orchestration, selected parsing, and evidence handoff
- Cross-tool MLP lifecycle, evidence review, and readiness methodology

These Domain Assistants provide guidance and may call optional helpers for
validation, templates, parsing, analysis, or artifact recording. The product
role does not make SimFlow a workflow executor.

GPUMD and NEP are helper-supported at the shared tool-support level for
bounded input preparation, static validation, dry-run planning, selected output
parsing, orchestration, manifest generation, and evidence handoff. This
includes helper-supported input generation and validation. GPUMD/NEP real execution,
local submit, remote execution, and HPC submit are not helper-supported
actions.

`workflow/toolchains/capabilities.json` is the source of truth for helper
support. `simflow.helper_evidence.v1` is an optional helper-script output
format, not a Domain Assistant classification or support level.

Software names outside this helper set do not block workflow planning or
artifact tracking. A shared toolchain contract records them as `tracked_only`
or `unknown` metadata and requires user-provided scripts, official
documentation, or custom artifacts for the scientific work.

For tracked-only or unknown tools, SimFlow provides generic evidence intake
rather than engine automation. Users or agents can register existing
computation scripts, inputs, validation summaries, dry-run reports, resource
estimates, outputs, environment metadata, analysis scripts, metrics, figures,
and QA reports so readiness and handoff remain traceable.

## Unsupported Placeholders

QE and Gaussian skills are reserved placeholders. They are packaged so users
receive a clear limitation message, but they are not supported computation,
analysis, validation, or stage-runner paths in this release.

If a user provides QE or Gaussian files, SimFlow may record them as generic
artifacts with explicit unsupported status. Do not advertise engine-specific
input generation, validation, parsing, or scientific conclusions for these
engines until product support and release tests are added.

The same boundary applies across DFT, AIMD, classical MD, phonon, NEB, and
MLP-MD recipes. Tools without dedicated execution helpers in this release,
including Quantum ESPRESSO, ABINIT, GROMACS, OpenMM, Phonopy, NEPTrainKit,
DeePMD, MACE, NequIP, and Allegro, may appear in proposal
toolchains and artifact provenance, but SimFlow does not provide
engine-specific execution automation for them yet.

## Execution Boundary

Real local, remote, or HPC execution is blocked unless SimFlow has dry-run
evidence, credential scan evidence, matching script/input hashes, and explicit
approval. Examples and CI should stay dry-run-only.

## Licensed And Large Scientific Artifacts

The repository must not contain real VASP `POTCAR`, `WAVECAR`, `CHGCAR`,
`OUTCAR`, or `vasprun.xml` artifacts. VASP examples may include redistributable
metadata placeholders only. Users must provide licensed files locally when they
run real calculations.

## Distribution Boundary

Codex and Claude marketplace branches are the current user-facing distribution
channels. PyPI is not the primary user install path until a package has been
published and install-smoked.

## Scientific Responsibility

SimFlow records evidence, lineage, checkpoints, safety gates, and handoff
context. The host agent and user remain responsible for scientific decisions,
interpretation, literature selection, model choices, and final claims.
