# Current Product Limitations

This page describes the current release boundary. It should be reviewed before
publishing release notes or marketplace branches.

## Supported Engine Helpers

The current product build supports optional domain helpers for:

- VASP
- CP2K
- LAMMPS

These helpers provide guidance, validation, templates, parsing, analysis, or
artifact-recording assistance. They remain optional helpers and do not make
SimFlow a workflow executor.

Software names outside this helper set do not block workflow planning or
artifact tracking. SimFlow records them as `tracked_only` or `unknown`
toolchain metadata and requires user-provided scripts, official documentation,
or custom artifacts for the scientific work.

## Unsupported Placeholders

QE and Gaussian skills are reserved placeholders. They are packaged so users
receive a clear limitation message, but they are not supported computation,
analysis, validation, or stage-runner paths in this release.

If a user provides QE or Gaussian files, SimFlow may record them as generic
artifacts with explicit unsupported status. Do not advertise engine-specific
input generation, validation, parsing, or scientific conclusions for these
engines until product support and release tests are added.

The same boundary applies to MLP tools without dedicated helpers in this
release, including GPUMD, NEP, NEPTrainKit, DeePMD, MACE, NequIP, and Allegro.
They may appear in proposal toolchains and artifact provenance, but SimFlow
does not provide engine-specific automation for them yet.

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
