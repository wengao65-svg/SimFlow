# SimFlow Technical Design

## Architecture Overview

```text
Codex / Claude Code / Host Agent
  -> SimFlow Skills
     intent recognition, evidence guidance, handoff discipline
  -> Workflow Layer
     open research stages, recipes, gates, policies
  -> MCP Recording Tools
     state, artifact, lineage, checkpoint, gate, handoff
  -> Runtime Helpers
     optional parsers, validators, templates, engine helpers
  -> .simflow/
     per-project state, artifacts, reports, checkpoints, logs
```

SimFlow is the state, evidence, and safety layer around computational research
work. It is not a central executor. The host agent remains responsible for
scientific judgment, code writing, source selection, analysis, and prose.

## Data Flow

1. A user request triggers one or more SimFlow skills.
2. The host agent identifies the current research stage and clarifies intent
   when needed.
3. SimFlow guidance states the minimum evidence and safety checks.
4. The agent performs the work using appropriate tools or custom code.
5. Artifacts are recorded with metadata, checksums, and lineage.
6. Stage boundaries create checkpoints.
7. High-risk actions are evaluated through gates and require recorded approval.
8. Handoff summaries capture state, artifacts, checkpoint, risks, and next
   steps.

## Component Responsibilities

- **Skills** provide intent-specific workflow guidance and evidence contracts.
- **Stages** describe research intent and expected evidence boundaries.
- **Recipes** describe optional reference paths such as DFT, AIMD, phonon, NEB,
  or classical MD.
- **Gates** enforce safety and traceability checks for risky actions.
- **Policies** define workflow-wide hard boundaries such as no credential
  storage.
- **MCP servers** record and retrieve state, artifacts, lineage, checkpoints,
  gates, and handoff data.
- **Runtime helpers** provide optional validators, templates, parsers, and
  engine-specific support.

## Technology Stack

- Python 3.10+ for runtime helpers and MCP servers
- JSON and JSON Schema for workflow contracts
- JSON recipe files for the current recipe migration
- Optional scientific libraries such as pymatgen, ASE, MDAnalysis, pandas, or
  matplotlib when available and appropriate
- MCP protocol for host-agent tool integration

## Boundary Rules

- `.simflow/` is the only SimFlow workflow state root.
- MCP write tools must receive explicit `project_root`.
- Plugin root and project root are separate.
- Real local, remote, or HPC execution requires approval.
- Credentials must not be persisted in SimFlow artifacts or logs.
- Scientific claims must trace back to literature, model, computation,
  analysis, or figure artifacts.
