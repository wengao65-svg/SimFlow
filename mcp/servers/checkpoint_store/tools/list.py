"""Compatibility shim for the pre-v0.12 checkpoint_store/list tool."""

from mcp.servers.simflow_state.tools.list_checkpoints import execute

__all__ = ["execute"]
