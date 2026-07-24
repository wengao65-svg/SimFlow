"""Session-level MCP engagement tracking for skill-MCP hard-binding.

This module enforces that state-write MCP tools (register, create_checkpoint,
update_stage, record_*_evidence, write_state) can only be called after a
read-only tool (read_state, workflow_status, etc.) has been called in the
same session. This prevents cargo-cult patterns where agents load SKILL.md
files as documentation but never engage the MCP tool layer.

Session tracking is file-backed (.simflow/state/mcp_engagement_log.jsonl)
so state survives MCP server restarts, with an in-memory cache for fast
lookups. Session timeout defaults to 30 minutes (configurable via
SIMFLOW_SESSION_TIMEOUT_MIN).
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from runtime.simflow_core.state import resolve_project_root

SESSION_TIMEOUT_SECONDS = int(os.environ.get("SIMFLOW_SESSION_TIMEOUT_MIN", "30")) * 60
ENGAGEMENT_LOG_FILENAME = "mcp_engagement_log.jsonl"

# Tools that ARE prerequisites (calling them satisfies the requirement)
PREREQUISITE_TOOLS = frozenset({
    "simflow_state/read_state",
})

# Tools that are exempt from prerequisites (read-only + init)
EXEMPT_TOOLS = frozenset({
    "simflow_state/init_workflow",
    "simflow_state/init_workflow_force",
    "simflow_state/read_state",
    "simflow_state/workflow_status",
    "simflow_state/stage_readiness",
    "simflow_state/evidence_graph",
    "simflow_state/handoff_summary",
    "simflow_state/project_readiness",
    "simflow_state/orphan_compute_scanner",
    "simflow_state/repair_state",
    "artifact_store/list",
    "artifact_store/get",
    "checkpoint_store/list",
    "hpc/dry_run",
    "hpc/status",
    "literature/search",
    "literature/get_metadata",
})

# Tools that REQUIRE prerequisites (state-write tools)
# Note: repair_state is exempt in audit mode; apply-mode protection will be
# added when the apply mode is implemented (it will check mode param).
PROTECTED_TOOLS = {
    "artifact_store/register": ["simflow_state/read_state"],
    "checkpoint_store/create": ["simflow_state/read_state"],
    "simflow_state/write_state": ["simflow_state/read_state"],
    "simflow_state/update_stage": ["simflow_state/read_state"],
    "simflow_state/record_computation_evidence": ["simflow_state/read_state"],
    "simflow_state/record_analysis_evidence": ["simflow_state/read_state"],
    "simflow_state/record_user_override": ["simflow_state/read_state"],
}


class EngagementViolation(Exception):
    """Raised when a protected tool is called without prerequisites met."""

    def __init__(self, tool: str, missing: list[str], session_start: Optional[str] = None):
        self.tool = tool
        self.missing = missing
        self.session_start = session_start
        super().__init__(
            f"skill_engagement_contract_violation: {tool} requires "
            f"{missing} to be called first in this session"
        )


def _log_path(project_root: str) -> Path:
    """Get the engagement log path for a project root."""
    root = resolve_project_root(project_root=project_root)
    return root / ".simflow" / "state" / ENGAGEMENT_LOG_FILENAME


def _append_log(project_root: str, entry: dict[str, Any]) -> None:
    """Append an entry to the engagement log (file-backed persistence)."""
    log_path = _log_path(project_root)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _read_recent_log(project_root: str, since_ts: float) -> list[dict[str, Any]]:
    """Read log entries newer than since_ts."""
    log_path = _log_path(project_root)
    if not log_path.exists():
        return []
    entries = []
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    entry_ts = entry.get("_ts_epoch", 0)
                    if entry_ts >= since_ts:
                        entries.append(entry)
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    return entries


def _now_epoch() -> float:
    return time.time()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def check_prerequisites(tool: str, project_root: str) -> None:
    """Check if prerequisites for a tool are met in the current session.

    Raises EngagementViolation if prerequisites are not met.
    Does nothing if the tool is exempt or not protected.
    """
    # Exempt tools never need prerequisites
    if tool in EXEMPT_TOOLS:
        return

    # If the tool is not in PROTECTED_TOOLS, it's not protected
    required = PROTECTED_TOOLS.get(tool)
    if not required:
        return

    # Check if prerequisites were met in this session
    session_start_ts = _now_epoch() - SESSION_TIMEOUT_SECONDS
    recent_entries = _read_recent_log(project_root, session_start_ts)

    # Find the latest session boundary (last activity > timeout ago = new session)
    session_start = None
    for entry in recent_entries:
        entry_ts = entry.get("_ts_epoch", 0)
        if session_start is None:
            session_start = entry_ts
        elif entry_ts - session_start > SESSION_TIMEOUT_SECONDS:
            session_start = entry_ts

    if session_start is None:
        # No activity in this session window at all
        raise EngagementViolation(tool, required, session_start=None)

    # Check which prerequisites were called in this session
    called_in_session = set()
    for entry in recent_entries:
        if entry.get("_ts_epoch", 0) >= session_start:
            called_in_session.add(entry.get("tool", ""))

    missing = [p for p in required if p not in called_in_session]
    if missing:
        session_start_iso = None
        for entry in recent_entries:
            if entry.get("_ts_epoch") == session_start:
                session_start_iso = entry.get("ts")
                break
        raise EngagementViolation(tool, missing, session_start=session_start_iso)


def record_tool_call(tool: str, project_root: str) -> None:
    """Record that a tool was called for a project root."""
    entry = {
        "ts": _now_iso(),
        "_ts_epoch": _now_epoch(),
        "tool": tool,
        "project_root": project_root,
    }
    _append_log(project_root, entry)


def get_engagement_status(project_root: str) -> dict[str, Any]:
    """Get the current engagement status for a project root (read-only)."""
    session_start_ts = _now_epoch() - SESSION_TIMEOUT_SECONDS
    recent_entries = _read_recent_log(project_root, session_start_ts)

    if not recent_entries:
        return {
            "has_session": False,
            "prerequisites_met": {},
            "session_start": None,
            "last_activity": None,
        }

    # Find session start
    session_start_epoch = recent_entries[0].get("_ts_epoch", 0)
    for entry in recent_entries:
        entry_ts = entry.get("_ts_epoch", 0)
        if entry_ts - session_start_epoch > SESSION_TIMEOUT_SECONDS:
            session_start_epoch = entry_ts

    called_in_session = set()
    last_activity = None
    session_start_iso = None
    for entry in recent_entries:
        if entry.get("_ts_epoch", 0) >= session_start_epoch:
            called_in_session.add(entry.get("tool", ""))
            if entry.get("ts"):
                last_activity = entry["ts"]
                if session_start_iso is None or entry.get("_ts_epoch") == session_start_epoch:
                    session_start_iso = entry["ts"]

    prereq_status = {}
    for prereq in PREREQUISITE_TOOLS:
        prereq_status[prereq] = prereq in called_in_session

    return {
        "has_session": True,
        "prerequisites_met": prereq_status,
        "session_start": session_start_iso,
        "last_activity": last_activity,
        "tools_called_in_session": sorted(called_in_session),
    }


def rotate_log(project_root: str, max_age_days: int = 7) -> int:
    """Rotate the engagement log, removing entries older than max_age_days.

    Returns the number of entries removed.
    """
    log_path = _log_path(project_root)
    if not log_path.exists():
        return 0

    cutoff_ts = _now_epoch() - (max_age_days * 86400)
    kept_entries = []
    removed_count = 0

    try:
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("_ts_epoch", 0) >= cutoff_ts:
                        kept_entries.append(line)
                    else:
                        removed_count += 1
                except json.JSONDecodeError:
                    continue
    except OSError:
        return 0

    if removed_count > 0:
        with open(log_path, "w", encoding="utf-8") as f:
            for line in kept_entries:
                f.write(line + "\n")

    return removed_count
