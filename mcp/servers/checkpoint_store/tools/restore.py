"""Compatibility shim for the pre-v0.12 checkpoint_store/restore tool."""

from mcp.servers.simflow_state.tools.restore_checkpoint import execute

__all__ = ["execute"]
