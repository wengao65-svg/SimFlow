# Runtime Scripts

This directory contains optional helper scripts and compatibility utilities for
local development, migration, and manual inspection.

The scripts are not the canonical top-level SimFlow entry point. In particular,
`simflow_cli.py` is a legacy/compatibility surface, not the recommended way to
run the current workflow layer.

The current integration model is:

- skills for user-facing workflow-layer behavior
- MCP/runtime helpers for explicit state and artifact operations
- `.simflow/` for project state, artifacts, checkpoints, lineage, gates, logs,
  and handoff reports

Helpers in this directory may be useful for tests, diagnostics, migration, or
ad hoc local workflows. They should not decide the scientific path, enforce a
fixed DFT/AIMD/MD DAG, or replace the host agent's reasoning.
