"""Metadata-only adapter contract registry."""

from __future__ import annotations

import json
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any

from runtime.simflow_core.toolchains import (
    helper_capabilities_for_tool,
    normalize_tool_name,
    support_level_for_tool,
)


ROOT = Path(__file__).resolve().parents[3]
ADAPTERS_CONTRACT_PATH = ROOT / "workflow" / "toolchains" / "adapters.json"


@lru_cache(maxsize=1)
def load_adapter_contract() -> dict[str, Any]:
    """Load the metadata-only active adapter contract."""
    with ADAPTERS_CONTRACT_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def _active_adapters() -> dict[str, dict[str, Any]]:
    contract = load_adapter_contract()
    adapters: dict[str, dict[str, Any]] = {}
    for adapter in contract.get("adapters", []):
        if isinstance(adapter, dict) and adapter.get("runtime_enabled") is True:
            adapters[normalize_tool_name(adapter.get("tool_id"))] = adapter
    return adapters


def _alias_index() -> dict[str, str]:
    index: dict[str, str] = {}
    for tool_id, adapter in _active_adapters().items():
        index[normalize_tool_name(tool_id)] = tool_id
        for alias in adapter.get("aliases", []):
            index[normalize_tool_name(alias)] = tool_id
    return index


def get_adapter(tool: str) -> dict[str, Any] | None:
    """Return adapter metadata for a tool without changing support policy."""
    tool_id = _alias_index().get(normalize_tool_name(tool))
    if not tool_id:
        return None
    adapter = deepcopy(_active_adapters()[tool_id])
    adapter["tool_support_level"] = support_level_for_tool({}, adapter["tool_id"])
    adapter["capability_contract"] = helper_capabilities_for_tool(adapter["tool_id"])
    return adapter


def list_adapters() -> list[dict[str, Any]]:
    """Return all runtime-enabled adapter metadata records."""
    return [adapter for key in sorted(_active_adapters()) if (adapter := get_adapter(key))]


def adapter_capabilities(tool: str) -> dict[str, Any]:
    """Return capability metadata with a stable empty result for unknown tools."""
    adapter = get_adapter(tool)
    if not adapter:
        normalized = normalize_tool_name(tool)
        return {
            "tool": normalized,
            "tool_support_level": support_level_for_tool({}, normalized),
            "supported_capabilities": [],
            "unsupported_capabilities": [],
            "evidence_roles_produced": [],
            "claim_limits": [],
            "handoff_targets": [],
        }
    return {
        "tool": adapter["tool_id"],
        "tool_support_level": adapter["tool_support_level"],
        "supported_capabilities": adapter["supported_capabilities"],
        "unsupported_capabilities": adapter["unsupported_capabilities"],
        "evidence_roles_produced": adapter["evidence_roles_produced"],
        "claim_limits": adapter["claim_limits"],
        "handoff_targets": adapter["handoff_targets"],
    }
