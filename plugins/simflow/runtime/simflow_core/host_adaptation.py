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
        "codex": "Describe the task naturally or invoke specific Skills directly. Use $simflow only to opt into SimFlow framework semantics; it does not route other Skills.",
        "claude_code": "Describe the task naturally or invoke namespaced Skills directly. Use /simflow:simflow only to opt into SimFlow framework semantics; it does not route other Skills.",
        "opencode": "Use OpenCode's skill tool for specific Skills. The host has no equivalent per-Skill explicit-only metadata, so load simflow manually only for framework semantics; it does not route other Skills.",
        "generic": "Discover and compose relevant Skills through the host. Use the SimFlow MCP tools only for tracked work.",
    }[host]
    invariants = (
        " Pass explicit project_root for runtime operations. When the request depends on existing"
        " SimFlow project truth, prior Experiment context, recovery state, or a durable runtime"
        " action, call read-only inspect once with project_root, working_directory, and the current"
        " query, then reuse the result for that request. Do not inspect merely because a Skill is active."
        " Do not create session state or print a fixed re-entry summary."
        " Bind a selected Experiment silently only when inspect reports an unambiguous match;"
        " resolve ambiguity before durable writes or execution binding."
        " Record only meaningful events; create checkpoints only at real recovery boundaries."
        " Real local, remote, or HPC execution remains dry-run-first and approval-gated."
        " SimFlow records runtime truth; the host remains responsible for scientific reasoning and execution."
    )
    return invocation + invariants
