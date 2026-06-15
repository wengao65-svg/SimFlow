"""Metadata-only helper adapter registry.

Adapters describe recognized files, evidence roles, claim limits, and
capability boundaries. They do not execute software, generate production
inputs, submit jobs, or replace skill guidance.
"""

from .registry import adapter_capabilities, get_adapter, list_adapters

__all__ = ["adapter_capabilities", "get_adapter", "list_adapters"]
