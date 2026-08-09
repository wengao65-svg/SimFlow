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
- run bounded helper operations such as dry-run validation and approved HPC
  file transfer

Avoid tools that claim to choose the best science for the user, such as
`choose_software`, `classify_vasp_task` as an authority, or
`generate_full_workflow` as a mandatory executor.

Remote file transfer is an explicit MCP boundary: use `hpc/upload` and
`hpc/download` with an approved `hpc_transfer` decision and verified SHA-256
manifest. The host agent should not implement routine remote transfer with
direct `scp` or `ssh` calls.

SSH operations receive a per-call `target` containing a required `host` and
optional `user` and `port`. The host may be an OpenSSH alias, hostname, or IP.
Omitted fields are not replaced with defaults, so OpenSSH configuration remains
effective. Upload, download, submit, and SSH status calls require this target.
It is included in approval bindings and transfer fingerprints. Passwords,
private-key content, key paths, and arbitrary SSH options are rejected.

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

The current wire-level server surface is `simflow_state` and `hpc`.
Artifact and checkpoint tools are consolidated into `simflow_state`.
Literature enrichment, structure operations, and parser helpers are
runtime/skill capabilities rather than MCP servers.

The names above describe architectural categories, not the current wire-level
tool names. See [MCP Tool Reference](mcp-tool-reference.md) for the actual
the `simflow_state/*` and `hpc/*` surface.

## Credentials

SSH authentication is delegated to the host OpenSSH client or a host-managed
agent through an internal Unix-socket broker. The Agent-facing `hpc` MCP does
not inherit `SSH_AUTH_SOCK` and never invokes the direct SSH connector. SimFlow
does not read SSH configuration or inspect private-key files. Credentials must
not be written to `.simflow/`, artifacts, reports, checkpoints, logs, or
generated handoff packages.

The broker accepts only versioned structured requests for status, cancellation,
transfer verification, upload/download, and approved submit. It has no generic
remote-shell operation. The socket is owner-only, peers are UID-checked, and
local file operations are confined to `SIMFLOW_HPC_BROKER_ALLOWED_ROOTS`.

## Host Adaptation

The shared MCP runtime reads standard `initialize.params.clientInfo` metadata.
The `simflow_state` server returns discovery guidance adapted to Codex, Claude
Code, or a generic MCP client. Only invocation syntax differs; project-root
boundaries, engagement prerequisites, artifact/checkpoint semantics, and safety
gates are host-invariant.

Host adaptation does not depend on skill-load hooks, transcript access, cwd,
plugin cache paths, or `.omx/`. Unknown clients receive generic guidance.
