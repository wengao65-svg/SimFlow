"""Compatibility shim for the pre-v0.12 artifact_store/get tool."""

from mcp.servers.simflow_state.tools.get_artifact import execute

__all__ = ["execute"]
