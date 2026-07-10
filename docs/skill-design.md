# Skill Design

## Purpose

SimFlow is skill-first. Skills are the user-facing entry points that help a host
agent recognize research intent, apply SimFlow evidence rules, and produce
handoff-ready work.

Skills are not workflow executors. They should not force one parser, one report
name, one builder, one simulation engine, or one fixed DFT/AIMD/MD path.

## Core Skill Set

The refactored workflow layer centers on a small core set:

- `simflow`
- `simflow-literature-review`
- `simflow-proposal`
- `simflow-modeling`
- `simflow-computation`
- `simflow-analysis-visualization`
- `simflow-writing`
- `simflow-safety-gates`

Engine-specific skills for VASP, CP2K, LAMMPS, and GPUMD/NEP are the supported
domain assistants in the current product build. `simflow-mlp` is a cross-tool
Domain Assistant for machine-learning-potential dataset, training, validation,
active-learning, deployment, and readiness methodology. These skills provide checklists,
templates, troubleshooting, validation suggestions, official-documentation
pointers, and artifact registration guidance. QE and Gaussian skills are
reserved unsupported placeholders that may only record user-provided files as
generic artifacts. Engine skills do not own workflow progression.

## Skill Contract

A SimFlow skill should describe:

- trigger conditions
- user intent it supports
- minimum evidence expected from the work
- common risks
- safety boundaries
- handoff requirements

It should avoid hard requirements such as:

- must use a specific parser script
- must use a specific builder
- must generate a fixed report filename
- must choose a fixed software package
- must map unknown tasks to a default known task

For example, an analysis skill may recommend built-in parser helpers while also
allowing the agent to write Python, use pandas, py4vasp, MDAnalysis, ASE,
pymatgen, matplotlib, or another appropriate tool. The hard requirement is that
the script, inputs, outputs, environment, and figure lineage are recorded.

## Domain Assistant Pattern

Domain Assistant is the Skill product role. It is independent from the helper
support level assigned to a concrete tool or capability in
`workflow/toolchains/capabilities.json`. A Domain Assistant may call optional
helper scripts, and those scripts may emit `simflow.helper_evidence.v1`; the
helper-evidence envelope is an output contract rather than a product class.

Domain Assistants should answer questions such as:

- What input files are commonly needed?
- Which checks are risky for this engine or method?
- What errors are common and how should they be diagnosed?
- Which artifacts should be registered?
- Which official references are useful?
- Which safety issues apply to proprietary files or licensed data?

They should return uncertainty when intent is unclear. For example, a VASP
phonon, NEB, SOC, hybrid, defect, or custom analysis request must not be
silently treated as a static calculation.

## Custom Skills

Users may add project-specific skills under `.simflow/extensions/skills/`.
Custom skills can override or supplement built-in guidance, but they inherit the
same hard boundaries:

- write state only under the explicit project `.simflow/` root
- register artifacts with metadata and lineage
- create checkpoints at stage boundaries
- require approval for real compute submission
- never store credentials
- never fabricate literature, data, figures, or citations

## Validation

Skill contract tests should check for the presence of evidence, artifact,
safety, and handoff language. They should also reject accidental hard-coded
requirements that make a helper the only valid path.

## Script Contract

Skill scripts are optional helpers. They are allowed to parse files, generate
templates, inspect outputs, or package reports, but they must not become the
canonical workflow executor. When a helper emits a shared evidence record, use
`simflow.helper_evidence.v1` without treating that schema as the Skill's
product identity or support level.

Canonical stage runners use this callable contract:

```python
run_<stage>_stage(workflow_dir: str, params: dict | None = None, dry_run: bool = True) -> dict
```

Executable helper CLIs must support:

- `--project-root` for explicit `.simflow/` recording
- `--stage` for the canonical evidence boundary
- `--record-helper-run` to opt into helper-run artifact and lineage recording

Without `--record-helper-run`, helper scripts should remain standalone and
avoid writing SimFlow state. With `--record-helper-run`, they must use
`runtime.simflow_core.helpers.record_helper_run` or the shared script-contract
wrapper so scripts, inputs, outputs, environment, and lineage are recorded.
