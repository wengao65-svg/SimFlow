# State and Checkpoint Management

## .simflow Directory Structure

```
.simflow/
├── state/
│   ├── workflow.json      # Overall workflow state
│   ├── stages.json        # Stage status registry
│   ├── artifacts.json     # Artifact registry
│   ├── checkpoints.json   # Checkpoint registry
│   ├── jobs.json          # HPC job tracking
│   ├── verification.json  # Gate verification state
│   ├── lineage.json       # First-class artifact nodes and links
│   ├── mcp_engagement_log.jsonl # Session-level MCP engagement evidence
│   └── summary.json       # Project status summary
├── artifacts/
│   ├── initial_structure.cif
│   ├── relaxed_structure.cif
│   └── energy.dat
├── checkpoints/
│   ├── relax_001.tar.gz
│   └── scf_001.tar.gz
├── reports/
│   └── status_summary.md
├── extensions/
│   └── skills/            # Custom skill overrides
├── logs/
│   └── workflow.log
└── config.json            # Local overrides
```

## State Lifecycle

1. **Initialize**: `simflow_state.init_workflow` creates the `.simflow/` tree, required state registries, and status summary files
2. **Running**: Stage transitions update stage status
3. **Completed**: Artifacts registered, checkpoint created
4. **Recovery**: Load last checkpoint, resume from that stage

Initialization is idempotent. Re-entering an existing project preserves its
state. An explicit `force=true` request first copies the current tree to
`.simflow/backups/<timestamp>/` before recreating canonical state files.

Artifact registration is a single state transaction: `artifacts.json`,
`lineage.json`, and the producing stage's `outputs` are updated together. Every
new artifact records its `workflow_id`.

Stage completion creates a pending verification record. Stage execution failure
uses `record_stage_failure`, which writes sanitized log and error-report
artifacts, marks workflow/stage summaries failed, creates a fail verification,
and creates a failure checkpoint with a separate recovery checkpoint reference.

## Ownership Boundaries

Canonical stage runners own stage transitions. Checkpoint/state-admin APIs own
checkpoint operations. Helper outputs are evidence-only by default; they may
write requested files under `project_root`, but they do not initialize or
advance stages, do not register artifacts, and do not create checkpoints
unless explicit helper-run recording is requested.

Default helper reports live under project-root `reports/<engine>/`. `.simflow`
is touched only by explicit helper-run recording.

`--record-helper-run` is `record_only`: it registers helper evidence and
lineage only. It does not mark a stage complete or failed and does not create
a stage-boundary checkpoint.

Direct helpers do not register arbitrary report artifacts. Stage runners may
ingest/register outputs when those outputs become canonical stage artifacts.

`simflow.result.v1` defines canonical nested roles, outcomes, and state
effects. Top-level statuses are compatibility fields rather than the canonical
cross-surface contract. Helper evidence status, stage status, verification
status, readiness status, gate status, and checkpoint status are distinct
vocabularies.

## Host State Boundary

`.omx/` is owned by oh-my-codex / the host session. SimFlow may read `.omx/` for host context, but `.omx/` is never the SimFlow workflow state root. Initializing SimFlow in a project that already contains `.omx/` must leave `.omx/` untouched and create or update only `.simflow/` for workflow state.

## Project Root Boundary

SimFlow distinguishes `plugin_root` from `project_root`. `plugin_root` is the installed plugin or cache directory used to import SimFlow code. `project_root` is the user's current working project and is where `.simflow/`, `reports/`, artifacts, and checkpoints are written. MCP servers may run with cwd set to `plugin_root`, so MCP tools must receive an explicit `project_root` and must reject attempts to write workflow state to the plugin root or plugin cache.

## Recovery Strategy

1. Find the latest successful, recoverable stage checkpoint
2. Extract artifacts from checkpoint
3. Update state to reflect recovered artifacts
4. Resume workflow from the next stage

Do not automatically restore the latest checkpoint by creation time: the newest
checkpoint may be a diagnostic failure snapshot. A checkpoint marked
`recoverable=false` is never restorable.

## State Schema

Workflow state follows `schemas/state.schema.json`. Projects use canonical
stages and may store DFT/AIMD/MD as `recipe` or `tags`.

```json
{
  "workflow_id": "wf_001",
  "workflow_type": "custom",
  "recipe": "dft",
  "tags": ["dft"],
  "status": "running",
  "current_stage": "computation",
  "stages": {
    "modeling": {"status": "completed"},
    "computation": {"status": "running"}
  },
  "artifacts": {
    "initial_structure": {"path": "...", "stage": "modeling"}
  },
  "created_at": "2026-05-01T10:00:00Z",
  "updated_at": "2026-05-01T10:05:00Z"
}
```
