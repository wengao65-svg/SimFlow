"""Shared software and toolchain contract helpers.

This module is the single source for SimFlow helper-support semantics. Recipes
may suggest tools and activity roles, but they must not define admission rules
or their own support-level logic.
"""

from __future__ import annotations

import json
from typing import Any

from .workflow import load_recipe


HELPER_SUPPORTED_SOFTWARE = {"vasp", "cp2k", "lammps"}
TOOL_ALIASES = {
    "qe": "quantum_espresso",
    "quantum-espresso": "quantum_espresso",
    "quantumespresso": "quantum_espresso",
    "open_mm": "openmm",
    "deep_md": "deepmd",
    "deepmd-kit": "deepmd",
    "nep_train_kit": "neptrainkit",
    "nep-train-kit": "neptrainkit",
}
TRACKED_ONLY_SOFTWARE = {
    "abinit",
    "allegro",
    "ase",
    "custom",
    "deepmd",
    "dpgen",
    "gpumd",
    "gromacs",
    "mace",
    "nep",
    "neptrainkit",
    "nequip",
    "openmm",
    "phonopy",
    "python",
    "quantum_espresso",
}


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
        "policy": "Only builtin helper software has SimFlow helper support; tracked-only and unknown tools are recorded for provenance and handoff.",
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
    return {
        "status": "capability_warning",
        "stage": stage,
        "capability": capability,
        "software": selected,
        "support_level": support_level,
        "message": (
            f"No built-in SimFlow helper is available for {selected} {capability}. "
            "Use user-provided scripts, official documentation, or custom artifacts; "
            "SimFlow will track provenance, evidence, and approval gates."
        ),
        "toolchain_plan": contract.get("toolchain_plan", {}),
        "helper_support": contract.get("helper_support") or contract.get("software_support", {}),
        "next_actions": [
            "Record the command, inputs, outputs, environment, and limitations as artifacts.",
            "Use dry-run and approval gates before any real local, remote, or HPC execution.",
        ],
    }
