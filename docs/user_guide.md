# SimFlow User Guide

## What SimFlow Does

SimFlow helps a host agent keep computational research traceable. It provides:

- canonical research stages
- `.simflow/` project state
- artifact metadata and lineage
- checkpoints and handoff notes
- dry-run-first safety gates for real execution
- optional domain helpers for common simulation software

It does not run a fixed workflow for you and does not choose the science. The
host agent chooses literature sources, modeling tools, simulation engines,
analysis scripts, plotting tools, and writing format.

## Invocation

SimFlow is skill-first. In Codex, use `$simflow`, `$simflow-vasp`, or natural
language that triggers a SimFlow skill. In Claude Code, use namespaced skills
such as `/simflow:simflow`.

Legacy runtime CLI scripts have been removed from the packaged source. User
work should enter through skills and, when needed, MCP/runtime helpers that
write explicit `.simflow/` state, artifacts, checkpoints, lineage, and gate
records. Do not treat SimFlow as a command-line workflow executor.

## Canonical Stages

| Stage | Purpose |
| --- | --- |
| `literature_review` | Track sources, search logs, notes, citation evidence, and review claims |
| `proposal` | Record research plan, assumptions, alternatives, resources, and risks |
| `modeling` | Preserve model sources and transformations |
| `computation` | Prepare, validate, dry-run, optionally submit, and record jobs |
| `analysis_visualization` | Record scripts, data, figures, interpretation, and lineage |
| `writing` | Map claims to evidence artifacts and mark speculation |

Any stage can be entered directly when the needed evidence is available.

## Recipes

DFT, AIMD, classical MD, phonon, NEB, and custom paths are recipes or tags. They
are reference paths, not fixed executor DAGs.

Current work should use canonical stages and recipes under `workflow/recipes/`.

## Software And Toolchains

Software names are proposal metadata, helper-routing hints, and artifact
provenance. They are not a required registry entry before a project can move
through SimFlow.

If a proposal names a helper-supported tool such as VASP, CP2K, or LAMMPS,
stage runners may use the corresponding helper path. If it names a
tracked-only or unknown tool, SimFlow should still record the plan, user
scripts, commands, outputs, versions, environment, limitations, and lineage.
Built-in stage runners return a `capability_warning` when automation is
requested for a tool without helper support.

After a `capability_warning`, record user-provided computation evidence through
the generic computation evidence intake path. The intake records existing
scripts, inputs, validation reports, dry-run reports, resource estimates,
commands, versions, environments, and limitations as computation artifacts. If
the required computation evidence is present, the computation stage can be
explicitly completed and checkpointed without adding a software-specific helper.

All recipes use the same toolchain contract. DFT, AIMD, classical MD, phonon,
NEB, and MLP-MD workflows may record single-tool or multi-tool plans in
`toolchain` or `toolchain_plan`, then record the concrete runtime fact in
artifact metadata as `actual_tool_used`. Recipe files can suggest activity
roles, but they do not define software support levels.

## Common Work Patterns

### Literature Review From User PDFs

Record uploaded PDFs, search/source logs, notes, citation maps, and review
summaries. Direct quotes, source claims, and agent interpretation should be
separate artifacts or clearly separated sections.

### User-Provided Structure

Register the original POSCAR/CIF/XYZ as a user-provided model artifact before
any transformation. If the agent uses ASE, pymatgen, Open Babel, or a custom
script, record the script/command, environment, output, and lineage.

### Computation

Before real local, remote, or HPC execution, record:

- calculation manifest
- input validation report
- dry-run report
- resource estimate
- credential scan
- script/input hashes
- gate decision id or approval token

A job record is only required after a real local, remote, or HPC submit has
occurred. Dry-run-only computation evidence does not need
`job_record_if_submitted`. When a real `hpc.submit` succeeds through the MCP
submit tool, SimFlow records a `job_record_if_submitted` computation artifact
with the scheduler job id, gate decision, approved hashes, script path, and
submit result.

The computation helper writes the gate evidence to canonical project-local
paths so later submit tools can verify the exact preparation state:

| Evidence | Path |
| --- | --- |
| Calculation manifest | `.simflow/artifacts/compute/calculation_manifest.json` |
| Input validation | `.simflow/artifacts/compute/input_validation.json` |
| Resource estimate | `.simflow/artifacts/compute/resource_estimate.json` |
| Dry-run report | `.simflow/artifacts/compute/dry_run_report.json` |
| Credential scan | `.simflow/artifacts/security/credential_scan.json` |

`dry_run_report.json` records `status`, `script_hash`, `input_artifact_hash`,
and `input_manifest_hash`. The compute plan also contains `submit_readiness`,
which names the dry-run evidence, script path, scheduler, and hashes expected by
the submit connector.

Changing the script or input hashes invalidates prior approval.

### Analysis And Figures

The agent may use built-in helpers or write custom Python. Either path must
record scripts, commands, inputs, outputs, environment, and figure lineage.
Incomplete outputs, failed convergence, missing frames, or speculative
interpretations must be labeled.

For tracked-only tools, custom notebooks, external post-processing suites, or
manually prepared figures, record evidence through generic analysis evidence
intake instead of adding a recipe-specific parser. The intake records analysis
scripts, input data, derived outputs, environment notes, figure files, figure
manifests, visual QA, and claim evidence maps as `analysis_visualization`
artifacts.

### Writing

Writing outputs can be a draft, proposal, internal report, figure captions,
slides, or another user-requested format. Key claims should trace to literature,
modeling, computation, analysis, or figure artifacts. Unfinished calculations
must not be written as completed results.

Writing claim maps include degraded evidence states such as `dry_run_only`,
`waiting_for_outputs`, `missing_evidence`, and `skipped_optional_dependency`.
These states are explicit reminders that the text may describe plans,
limitations, or pending evidence, but must not present those items as completed
scientific results.

## Environment Variables

| Variable | Purpose |
| --- | --- |
| `MP_API_KEY` | Materials Project API key |
| `S2_API_KEY` | Semantic Scholar API key |
| `SIMFLOW_SSH_HOST` | SSH HPC host |
| `SIMFLOW_SSH_USER` | SSH username |
| `SIMFLOW_SSH_KEY` | SSH key file path |

Credentials may be read from the environment but must not be stored in
`.simflow/`, artifacts, reports, checkpoints, logs, or handoff packages.
