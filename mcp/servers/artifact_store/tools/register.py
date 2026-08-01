"""Compatibility shim for the pre-v0.12 artifact_store/register tool."""

from mcp.servers.simflow_state.tools.register_artifact import execute

__all__ = ["execute"]
