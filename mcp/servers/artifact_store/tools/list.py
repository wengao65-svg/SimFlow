"""Compatibility shim for the pre-v0.12 artifact_store/list tool."""

from mcp.servers.simflow_state.tools.list_artifacts import execute

__all__ = ["execute"]
