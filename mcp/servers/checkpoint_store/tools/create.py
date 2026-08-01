"""Compatibility shim for the pre-v0.12 checkpoint_store/create tool."""

from mcp.servers.simflow_state.tools.create_checkpoint import execute

__all__ = ["execute"]
