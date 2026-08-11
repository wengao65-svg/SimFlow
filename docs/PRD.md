# SimFlow Product Requirements Document

## Product

SimFlow is a host-neutral computational-research guidance, provenance,
recovery, and execution-safety layer. It improves how an agent performs
scientific tasks without becoming the scientific reasoner or a centralized
workflow executor.

## Users

- researchers using coding agents for simulation projects;
- teams that need compact cross-session project truth and recovery references;
- users who need dry-run-first local, remote, and HPC execution discipline;
- projects that already have established directory layouts and scripts.

## Required Capabilities

1. One thin router, six Research Task Skills, and five Domain Skills.
2. Task and Domain Skills that work without MCP and never own runtime state.
3. Four compact state tools: inspect, record, checkpoint, recover.
4. Four execution tools: plan, transfer, submit, status.
5. Append-only operational records plus one append-only Markdown notebook per
   scientific Experiment.
6. A deterministic project-summary rebuild from notebooks, operational records,
   and compact recovery references.
7. Approval bound to an immutable run-plan hash and reusable only while the
   plan remains unchanged.
8. Read-only legacy state discovery and explicit non-destructive migration.
9. Existing-layout-first project organization with optional six-phase guidance.
10. Credential isolation and metadata-only handling of licensed POTCAR.
11. Experiment identity based on a scientific question rather than parameter
    dimensions such as temperature, element, seed, retry, or resume.

## Domain Boundary

Built-in Domain Skills cover VASP, CP2K, LAMMPS, GPUMD/NEP, and general MLP
methodology. Unsupported engines use the relevant Task Skill with explicit
uncertainty. Placeholder Skills are not shipped.

## Success Criteria

- ordinary read-only research produces zero SimFlow writes;
- ordinary file preparation or analysis needs at most one logical record;
- experiment notebooks preserve scientific intent, observations, decisions,
  material evidence changes, uncertainty, and next actions across host sessions;
- exact scientific files remain the evidence source and are referenced by
  project-relative path and hash rather than copied into notebooks;
- each task selects at most one Task Skill and one Domain Skill;
- remote execution uses at most plan, transfer, submit, and status;
- unchanged retries do not repeat approval, while material changes do;
- checkpoint files contain recovery references, not full state snapshots;
- old projects continue without directory migration;
- POTCAR bodies, credentials, and private-key paths never enter state or
  distribution packages;
- no runtime surface claims that submission, output presence, or parser success
  proves scientific completion.
- experiment and attempt bindings never change an immutable run-plan hash.
