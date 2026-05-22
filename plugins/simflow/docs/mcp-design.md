# MCP Server Design

## Role

SimFlow MCP servers provide recording, validation, and state-management tools.
They should not decide the scientific path for the host agent.

Recommended MCP responsibilities:

- initialize and read project workflow state
- record artifacts and metadata
- link lineage between artifacts
- create and list checkpoints
- evaluate and record safety gate decisions
- summarize handoff status
- run bounded helper operations such as dry-run validation

Avoid tools that claim to choose the best science for the user, such as
`choose_software`, `classify_vasp_task` as an authority, or
`generate_full_workflow` as a mandatory executor.

## Project Root Boundary

Every write operation must receive `project_root` explicitly. MCP servers often
run with cwd set to the plugin root or cache directory, and that cwd is not the
user project.

Write tools must reject:

- missing `project_root`
- the SimFlow plugin root used as `project_root`
- attempts to write SimFlow workflow state outside the project `.simflow/` root

The plugin root is only for importing code and reading bundled assets.

## Tool Schema Policy

MCP `tools/list` responses must expose real input schemas. Empty schemas with
`additionalProperties: true` are not sufficient for write tools because agents
cannot see required fields or safety boundaries.

Example target schema:

```json
{
  "name": "simflow.artifact.record",
  "inputSchema": {
    "type": "object",
    "required": ["project_root", "stage", "artifact_type", "path"],
    "properties": {
      "project_root": {"type": "string"},
      "stage": {"type": "string"},
      "artifact_type": {"type": "string"},
      "path": {"type": "string"},
      "metadata": {"type": "object"}
    },
    "additionalProperties": false
  }
}
```

## Server Categories

The high-level target surface is:

- `simflow.project.init`
- `simflow.workflow.status`
- `simflow.workflow.advance`
- `simflow.artifact.record`
- `simflow.artifact.list`
- `simflow.lineage.link`
- `simflow.checkpoint.create`
- `simflow.gate.evaluate`
- `simflow.gate.record_decision`
- `simflow.handoff.summarize`

Existing servers may keep backward-compatible names during migration, but their
behavior should converge on explicit project roots, strict schemas, and
evidence-based recording.

## Credentials

Credentials are read from environment variables or host-managed secret stores.
They must not be written to `.simflow/`, artifacts, reports, checkpoints, logs,
or generated handoff packages.
