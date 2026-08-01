#!/usr/bin/env python3
"""Tests for skill-MCP hard-binding engagement contract.

Covers P0.7:
- State-write tools are blocked unless read_state was called in the same session
- Read-only tools are exempt and always succeed
- Session timeout (30 min) resets prerequisites
- Engagement log is file-backed (survives MCP server restart)
- Violation returns clear error message with missing prerequisites
"""

import os
import sys
import time
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]  # tests/ -> simflow/
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runtime"))


def _init_workflow(project_root):
    from runtime.simflow_core.state import init_workflow
    return init_workflow("custom", "computation", project_root=project_root)


# ============================================================
# Engagement module unit tests
# ============================================================

def test_exempt_tools_never_blocked():
    """Exempt tools (read_state, workflow_status, etc.) pass check_prerequisites."""
    from runtime.simflow_core.engagement import check_prerequisites, EXEMPT_TOOLS

    with tempfile.TemporaryDirectory() as tmpdir:
        _init_workflow(tmpdir)
        for tool in EXEMPT_TOOLS:
            # Should NOT raise
            check_prerequisites(tool, tmpdir)


def test_protected_tools_blocked_without_read_state():
    """State-write tools are blocked when read_state hasn't been called."""
    from runtime.simflow_core.engagement import (
        check_prerequisites, EngagementViolation, PROTECTED_TOOLS,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        _init_workflow(tmpdir)
        for tool in PROTECTED_TOOLS:
            with pytest.raises(EngagementViolation) as exc_info:
                check_prerequisites(tool, tmpdir)
            assert "simflow_state/read_state" in exc_info.value.missing


def test_protected_tools_allowed_after_read_state():
    """State-write tools succeed after read_state was called in the same session."""
    from runtime.simflow_core.engagement import (
        check_prerequisites, record_tool_call, PROTECTED_TOOLS,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        _init_workflow(tmpdir)
        # Record a read_state call
        record_tool_call("simflow_state/read_state", tmpdir)

        # All protected tools should now pass
        for tool in PROTECTED_TOOLS:
            check_prerequisites(tool, tmpdir)  # Should NOT raise


def test_session_timeout_resets_prerequisites():
    """Prerequisites reset after session timeout (30 min by default)."""
    from runtime.simflow_core.engagement import (
        check_prerequisites, record_tool_call, EngagementViolation,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        _init_workflow(tmpdir)
        # Record read_state with old timestamp (simulated)
        from runtime.simflow_core.engagement import _append_log, _now_epoch
        old_ts = _now_epoch() - 3600  # 1 hour ago (past 30-min timeout)
        _append_log(tmpdir, {
            "ts": "2026-01-01T00:00:00Z",
            "_ts_epoch": old_ts,
            "tool": "simflow_state/read_state",
            "project_root": tmpdir,
        })

        # read_state is too old, should be blocked
        with pytest.raises(EngagementViolation):
            check_prerequisites("simflow_state/register_artifact", tmpdir)


def test_engagement_log_is_file_backed():
    """Engagement log is persisted to .simflow/state/mcp_engagement_log.jsonl."""
    from runtime.simflow_core.engagement import record_tool_call, _log_path

    with tempfile.TemporaryDirectory() as tmpdir:
        _init_workflow(tmpdir)
        record_tool_call("simflow_state/read_state", tmpdir)

        log_path = _log_path(tmpdir)
        assert log_path.exists()
        content = log_path.read_text(encoding="utf-8").strip()
        assert "read_state" in content
        assert "project_root" in content


def test_get_engagement_status_empty():
    """get_engagement_status returns no session for fresh project."""
    from runtime.simflow_core.engagement import get_engagement_status

    with tempfile.TemporaryDirectory() as tmpdir:
        _init_workflow(tmpdir)
        status = get_engagement_status(tmpdir)
        assert status["has_session"] is False


def test_get_engagement_status_after_read_state():
    """get_engagement_status shows prerequisites met after read_state."""
    from runtime.simflow_core.engagement import record_tool_call, get_engagement_status

    with tempfile.TemporaryDirectory() as tmpdir:
        _init_workflow(tmpdir)
        record_tool_call("simflow_state/read_state", tmpdir)

        status = get_engagement_status(tmpdir)
        assert status["has_session"] is True
        assert status["prerequisites_met"]["simflow_state/read_state"] is True
        assert "simflow_state/read_state" in status["tools_called_in_session"]


def test_log_rotation_removes_old_entries():
    """rotate_log removes entries older than max_age_days."""
    from runtime.simflow_core.engagement import (
        record_tool_call, _append_log, _now_epoch, rotate_log, get_engagement_status,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        _init_workflow(tmpdir)
        # Add an old entry (10 days ago)
        _append_log(tmpdir, {
            "ts": "2026-01-01T00:00:00Z",
            "_ts_epoch": _now_epoch() - 10 * 86400,
            "tool": "simflow_state/read_state",
            "project_root": tmpdir,
        })
        # Add a recent entry
        record_tool_call("simflow_state/read_state", tmpdir)

        removed = rotate_log(tmpdir, max_age_days=7)
        assert removed == 1

        # Recent entry should still be there
        status = get_engagement_status(tmpdir)
        assert status["has_session"] is True


# ============================================================
# MCP server integration tests
# ============================================================

MCP_STATE_DIR = ROOT / "mcp" / "servers" / "simflow_state"


def _load_state_server():
    """Load the simflow_state server module fresh."""
    import importlib.util
    state_dir = str(MCP_STATE_DIR)
    if state_dir in sys.path:
        sys.path.remove(state_dir)
    sys.path.insert(0, state_dir)
    spec = importlib.util.spec_from_file_location(
        "simflow_state_server_test_engagement",
        str(MCP_STATE_DIR / "server.py"),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_mcp_register_blocked_without_read_state():
    """simflow_state/register_artifact is blocked without prior read_state."""
    state_server = _load_state_server()

    with tempfile.TemporaryDirectory() as tmpdir:
        _init_workflow(tmpdir)

        # Try to register without read_state
        result = state_server.handle_request({
            "tool": "register_artifact",
            "params": {
                "project_root": tmpdir,
                "name": "test.txt",
                "type": "test_file",
                "stage": "computation",
            },
        })

        assert result["status"] == "error"
        assert result["code"] == "skill_engagement_contract_violation"
        assert "read_state" in result["message"]


def test_mcp_register_allowed_after_read_state():
    """simflow_state/register_artifact succeeds after read_state was called."""
    # First call read_state via simflow_state server
    for k in [k for k in sys.modules if k == "server" or k == "tools" or k.startswith("tools.")]:
        del sys.modules[k]

    MCP_STATE_DIR_STR = str(MCP_STATE_DIR)
    if MCP_STATE_DIR_STR in sys.path:
        sys.path.remove(MCP_STATE_DIR_STR)
    sys.path.insert(0, MCP_STATE_DIR_STR)

    state_server = _load_state_server()

    with tempfile.TemporaryDirectory() as tmpdir:
        _init_workflow(tmpdir)

        # Call read_state first
        read_result = state_server.handle_request({
            "tool": "read_state",
            "params": {"project_root": tmpdir, "file": "workflow.json"},
        })
        assert read_result["status"] == "success"

        # Create a test file
        test_file = Path(tmpdir) / "test.txt"
        test_file.write_text("content", encoding="utf-8")

        result = state_server.handle_request({
            "tool": "register_artifact",
            "params": {
                "project_root": tmpdir,
                "name": "test.txt",
                "type": "test_file",
                "stage": "computation",
                "path": "test.txt",
            },
        })

        assert result["status"] == "success", f"expected success, got: {result}"


def test_mcp_read_state_always_allowed():
    """simflow_state/read_state is exempt and always allowed."""
    for k in [k for k in sys.modules if k == "server" or k == "tools" or k.startswith("tools.")]:
        del sys.modules[k]

    state_server = _load_state_server()

    with tempfile.TemporaryDirectory() as tmpdir:
        _init_workflow(tmpdir)

        # read_state should work even without prior read_state
        result = state_server.handle_request({
            "tool": "read_state",
            "params": {"project_root": tmpdir, "file": "workflow.json"},
        })
        assert result["status"] == "success"


def test_mcp_workflow_status_always_allowed():
    """simflow_state/workflow_status is exempt and always allowed."""
    for k in [k for k in sys.modules if k == "server" or k == "tools" or k.startswith("tools.")]:
        del sys.modules[k]

    state_server = _load_state_server()

    with tempfile.TemporaryDirectory() as tmpdir:
        _init_workflow(tmpdir)

        result = state_server.handle_request({
            "tool": "workflow_status",
            "params": {"project_root": tmpdir},
        })
        assert result["status"] == "success"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
