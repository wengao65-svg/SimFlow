"""Shared software and toolchain contract helpers.

This module is the single source for SimFlow helper-support semantics. Recipes
may suggest tools and activity roles, but they must not define admission rules
or their own support-level logic.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from .workflow import load_recipe


ROOT = Path(__file__).resolve().parents[2]
CAPABILITIES_CONTRACT_PATH = ROOT / "workflow" / "toolchains" / "capabilities.json"


@lru_cache(maxsize=1)
def load_toolchain_capabilities() -> dict[str, Any]:
    """Load the shared toolchain capability contract."""
    with CAPABILITIES_CONTRACT_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


_CAPABILITY_CONTRACT = load_toolchain_capabilities()
HELPER_SUPPORTED_SOFTWARE = set(_CAPABILITY_CONTRACT.get("helper_supported_software", []))
CAPABILITY_SUPPORTED_TOOLS = set(_CAPABILITY_CONTRACT.get("capability_supported_tools", []))
HELPER_SUPPORTED_CAPABILITIES = {
    tool: set(value.get("supported", []))
    for tool, value in _CAPABILITY_CONTRACT.get("capability_support", {}).items()
}
BLOCKED_HELPER_CAPABILITIES = {
    tool: set(value.get("not_helper_supported", []))
    for tool, value in _CAPABILITY_CONTRACT.get("capability_support", {}).items()
}
TOOL_ALIASES = dict(_CAPABILITY_CONTRACT.get("aliases", {}))
TRACKED_ONLY_SOFTWARE = set(_CAPABILITY_CONTRACT.get("tracked_only_software", []))


def normalize_tool_name(value: Any) -> str:
    """Normalize user-provided software/tool names to stable internal ids."""
    normalized = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    return TOOL_ALIASES.get(normalized, normalized)


def coerce_toolchain(value: Any) -> list[str]:
    """Normalize a string, JSON-ish object, or sequence into tool ids."""
    if value in (None, ""):
        return []
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            parsed = value.replace(";", ",").split(",")
        return [tool for tool in (normalize_tool_name(item) for item in coerce_toolchain(parsed)) if tool]
    if isinstance(value, dict):
        raw_tools = value.get("tools") or value.get("software") or value.get("stack") or []
        return coerce_toolchain(raw_tools)
    if isinstance(value, (list, tuple, set)):
        tools: list[str] = []
        for item in value:
            if isinstance(item, dict):
                name = item.get("name") or item.get("software") or item.get("tool")
                if name:
                    tools.append(normalize_tool_name(name))
            else:
                tools.append(normalize_tool_name(item))
        return [tool for tool in tools if tool]
    return [normalize_tool_name(value)]


def extract_toolchain(metadata: dict[str, Any], parameter_values: dict[str, Any]) -> list[str]:
    """Extract ordered, de-duplicated toolchain metadata."""
    tools: list[str] = []
    for value in (
        metadata.get("toolchain"),
        metadata.get("software_stack"),
        parameter_values.get("toolchain"),
        parameter_values.get("software_stack"),
    ):
        tools.extend(coerce_toolchain(value))
    software = normalize_tool_name(metadata.get("software") or parameter_values.get("software") or "")
    if software and software != "custom":
        tools.insert(0, software)
    seen: set[str] = set()
    return [tool for tool in tools if tool and not (tool in seen or seen.add(tool))]


def classify_tool_support(toolchain: list[str]) -> dict[str, Any]:
    """Classify tools without blocking unknown or tracked-only tools."""
    builtin = [tool for tool in toolchain if tool in HELPER_SUPPORTED_SOFTWARE]
    tracked_only = [
        tool
        for tool in toolchain
        if tool not in HELPER_SUPPORTED_SOFTWARE and tool in TRACKED_ONLY_SOFTWARE
    ]
    unknown = [
        tool
        for tool in toolchain
        if tool not in HELPER_SUPPORTED_SOFTWARE and tool not in TRACKED_ONLY_SOFTWARE
    ]
    return {
        "builtin_helpers": builtin,
        "tracked_only": tracked_only,
        "unknown": unknown,
        "support_levels": {
            **{tool: "helper_supported" for tool in builtin},
            **{tool: "tracked_only" for tool in tracked_only},
            **{tool: "unknown" for tool in unknown},
        },
        "policy": "Built-in helper software has SimFlow helper support; tracked-only and unknown tools are recorded for provenance and handoff.",
    }


def support_level_for_tool(contract_or_support: dict[str, Any], tool: str | None = None) -> str:
    """Return helper support level for a tool or loaded proposal contract."""
    normalized = normalize_tool_name(tool or contract_or_support.get("software") or "custom")
    support = (
        contract_or_support.get("helper_support")
        or contract_or_support.get("software_support")
        or contract_or_support
        or {}
    )
    levels = support.get("support_levels", {})
    if normalized in levels:
        return levels[normalized]
    if normalized in HELPER_SUPPORTED_SOFTWARE:
        return "helper_supported"
    if normalized in TRACKED_ONLY_SOFTWARE:
        return "tracked_only"
    return "unknown"


def helper_capabilities_for_tool(tool: str) -> dict[str, Any]:
    """Return capability-level helper support without changing tool-level support."""
    normalized = normalize_tool_name(tool)
    supported = sorted(HELPER_SUPPORTED_CAPABILITIES.get(normalized, set()))
    blocked = sorted(BLOCKED_HELPER_CAPABILITIES.get(normalized, set()))
    return {
        "tool": normalized,
        "tool_support_level": support_level_for_tool({}, normalized),
        "supported_capabilities": supported,
        "blocked_capabilities": blocked,
        "policy": (
            "Capability support is governed by the shared toolchain contract. "
            "Real execution and submit still require safety-gate evidence."
        ),
    }


def support_level_for_capability(tool: str, capability: str) -> str:
    """Classify a specific helper capability for a tool."""
    normalized = normalize_tool_name(tool)
    capability_id = normalize_tool_name(capability)
    if capability_id in HELPER_SUPPORTED_CAPABILITIES.get(normalized, set()):
        return "helper_supported"
    if capability_id in BLOCKED_HELPER_CAPABILITIES.get(normalized, set()):
        return "not_helper_supported"
    return support_level_for_tool({}, normalized)


def _recipe_toolchain_activities(workflow_type: str) -> dict[str, list[str]]:
    try:
        recipe = load_recipe(normalize_tool_name(workflow_type) or "dft")
    except FileNotFoundError:
        return {}
    activities = recipe.get("metadata", {}).get("toolchain_activities", {})
    if not isinstance(activities, dict):
        return {}
    normalized: dict[str, list[str]] = {}
    for activity, tools in activities.items():
        if not isinstance(activity, str):
            continue
        normalized_tools = coerce_toolchain(tools)
        if normalized_tools:
            normalized[activity] = normalized_tools
    return normalized


def build_toolchain_plan(workflow_type: str, software: str, toolchain: list[str]) -> dict[str, Any]:
    """Build activity-level tool suggestions without becoming an executor DAG."""
    provided = toolchain or ([software] if software and software != "custom" else [])
    activities = _recipe_toolchain_activities(workflow_type)
    if activities:
        planned = {
            activity: [tool for tool in provided if tool in allowed] or allowed
            for activity, allowed in activities.items()
        }
    else:
        planned = {"primary": provided or ([software] if software else ["custom"])}

    return {
        "plan_id": "toolchain_plan_001",
        "source": "proposal_metadata",
        "policy": "Recommended activity-level tool choices; this is not an executor DAG and does not define helper support.",
        "activities": planned,
    }


def build_actual_tool_used(
    contract: dict[str, Any],
    tool: str | None = None,
    *,
    command: str | None = None,
    version: str | None = None,
    environment: Any = None,
) -> dict[str, Any]:
    """Build stable artifact metadata for the concrete runtime tool fact."""
    selected = normalize_tool_name(tool or contract.get("software") or "custom")
    return {
        "name": selected,
        "support_level": support_level_for_tool(contract, selected),
        "command": command,
        "version": version,
        "environment": environment,
    }


def capability_warning(
    contract: dict[str, Any],
    stage: str,
    capability: str,
    tool: str | None = None,
) -> dict[str, Any]:
    """Build a non-fatal warning when no helper supports a requested capability."""
    selected = normalize_tool_name(tool or contract.get("software") or "custom")
    support_level = support_level_for_tool(contract, selected)
    capability_support_level = support_level_for_capability(selected, capability)
    return {
        "status": "capability_warning",
        "stage": stage,
        "capability": capability,
        "software": selected,
        "support_level": support_level,
        "capability_support_level": capability_support_level,
        "message": (
            f"No built-in SimFlow helper is available for {selected} {capability}. "
            "Use user-provided scripts, official documentation, or custom artifacts; "
            "SimFlow will track provenance, evidence, and approval gates."
        ),
        "toolchain_plan": contract.get("toolchain_plan", {}),
        "helper_support": contract.get("helper_support") or contract.get("software_support", {}),
        "next_actions": [
            "Use the generic computation evidence intake to record user-provided scripts, inputs, dry-run evidence, resources, environment, and limitations.",
            "Use dry-run and approval gates before any real local, remote, or HPC execution.",
        ],
    }
