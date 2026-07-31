"""Host-neutral MCP initialization guidance with lightweight host detection."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal


HostKind = Literal["codex", "claude_code", "opencode", "generic"]


def detect_host(client_info: Mapping[str, Any] | None) -> HostKind:
    """Detect a supported host from standard MCP clientInfo metadata."""
    name = str((client_info or {}).get("name", "")).strip().lower()
    if "codex" in name:
        return "codex"
    if "claude" in name or "anthropic" in name:
        return "claude_code"
    if "opencode" in name:
        return "opencode"
    return "generic"


def build_initialize_instructions(
    server_name: str,
    client_info: Mapping[str, Any] | None,
) -> str | None:
    """Return host-adapted discovery guidance for the state server only."""
    if server_name != "simflow_state":
        return None
    host = detect_host(client_info)
    invocation = {
        "codex": "Use $simflow or a domain skill such as $simflow-vasp, or describe the task naturally.",
        "claude_code": "Use /simflow:simflow or a namespaced domain skill, or describe the task naturally.",
        "opencode": "Use OpenCode's skill tool to load simflow or a domain skill such as simflow-vasp, or describe the task naturally.",
        "generic": "Describe the simulation task naturally and use the SimFlow MCP tools for tracked work.",
    }[host]
    invariants = (
        " Pass explicit project_root. For an existing project, start with workflow_status or read_state."
        " Register tracked artifacts and create checkpoints at stage boundaries."
        " Real local, remote, or HPC execution remains dry-run-first and approval-gated."
        " SimFlow records workflow evidence; the host remains responsible for scientific reasoning and execution."
    )
    return invocation + invariants
