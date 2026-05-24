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

## Recipes And Legacy Workflows

DFT, AIMD, classical MD, phonon, NEB, and custom paths are recipes or tags. They
are reference paths, not fixed executor DAGs.

The repository no longer ships legacy `workflow/workflows/*.json` examples.
SimFlow can still migrate user-provided legacy workflow definitions and old
`.simflow/` state, but new work should use canonical stages and recipes.

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

Changing the script or input hashes invalidates prior approval.

### Analysis And Figures

The agent may use built-in helpers or write custom Python. Either path must
record scripts, commands, inputs, outputs, environment, and figure lineage.
Incomplete outputs, failed convergence, missing frames, or speculative
interpretations must be labeled.

### Writing

Writing outputs can be a draft, proposal, internal report, figure captions,
slides, or another user-requested format. Key claims should trace to literature,
modeling, computation, analysis, or figure artifacts. Unfinished calculations
must not be written as completed results.

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
