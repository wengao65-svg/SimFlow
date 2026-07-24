#!/usr/bin/env python3
"""Tests for P3.1 auto-read_state and P3.2 session_handoff tool.

P3.1: When a read-only tool is called first, read_state is auto-recorded
      so subsequent state-write tools don't get blocked.
P3.2: session_handoff generates a report with state summary, warnings,
      and next steps.
"""

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runtime"))
sys.path.insert(0, str(ROOT / "mcp" / "servers" / "simflow_state"))


def _init(project_root):
    from runtime.simflow_core.state import init_workflow
    return init_workflow("custom", "computation", project_root=project_root)


def _load_server():
    import importlib.util
    MCP_DIR = ROOT / "mcp" / "servers" / "simflow_state"
    # Purge cached modules
    for k in [k for k in sys.modules if k == "server" or k == "tools" or k.startswith("tools.")]:
        del sys.modules[k]
    spec = importlib.util.spec_from_file_location(
        "simflow_state_server_test_p3",
        str(MCP_DIR / "server.py"),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ============================================================
# P3.1: Auto-read_state on first call to read-only tools
# ============================================================

def test_workflow_status_auto_records_read_state():
    """Calling workflow_status first auto-records read_state, satisfying
    prerequisites for subsequent state-write tools."""
    server = _load_server()

    with tempfile.TemporaryDirectory() as tmpdir:
        _init(tmpdir)

        # Call workflow_status (read-only, no prior engagement)
        result = server.handle_request({
            "tool": "workflow_status",
            "params": {"project_root": tmpdir},
        })
        assert result["status"] == "success"

        # Now try update_stage (state-write) — should succeed because
        # read_state was auto-recorded by the workflow_status call
        result = server.handle_request({
            "tool": "update_stage",
            "params": {
                "project_root": tmpdir,
                "stage_name": "computation",
                "status": "in_progress",
            },
        })
        assert result["status"] == "success", f"update_stage should succeed after workflow_status auto-read: {result}"


def test_stage_readiness_auto_records_read_state():
    """Calling stage_readiness first also auto-records read_state."""
    server = _load_server()

    with tempfile.TemporaryDirectory() as tmpdir:
        _init(tmpdir)

        # Call stage_readiness (read-only)
        result = server.handle_request({
            "tool": "stage_readiness",
            "params": {"project_root": tmpdir},
        })
        assert result["status"] == "success"

        # Now try write_state — should succeed
        result = server.handle_request({
            "tool": "write_state",
            "params": {
                "project_root": tmpdir,
                "file": "metadata.json",
                "data": {"test": True},
            },
        })
        assert result["status"] == "success", f"write_state should succeed: {result}"


def test_explicit_read_state_still_works():
    """Explicit read_state call still works (no double-auto-record issue)."""
    server = _load_server()

    with tempfile.TemporaryDirectory() as tmpdir:
        _init(tmpdir)

        # Explicit read_state
        result = server.handle_request({
            "tool": "read_state",
            "params": {"project_root": tmpdir, "file": "workflow.json"},
        })
        assert result["status"] == "success"

        # update_stage should work
        result = server.handle_request({
            "tool": "update_stage",
            "params": {
                "project_root": tmpdir,
                "stage_name": "computation",
                "status": "in_progress",
            },
        })
        assert result["status"] == "success"


# ============================================================
# P3.2: session_handoff tool
# ============================================================

def test_session_handoff_generates_report():
    """session_handoff generates a markdown report with state summary."""
    server = _load_server()

    with tempfile.TemporaryDirectory() as tmpdir:
        _init(tmpdir)

        result = server.handle_request({
            "tool": "session_handoff",
            "params": {"project_root": tmpdir},
        })

        assert result["status"] == "success"
        assert "report_path" in result["data"]
        report_path = Path(tmpdir) / result["data"]["report_path"]
        assert report_path.exists()
        content = report_path.read_text(encoding="utf-8")
        assert "Session Handoff" in content
        assert "Workflow State" in content
        assert "Counts" in content


def test_session_handoff_includes_latest_checkpoint():
    """session_handoff includes latest checkpoint info."""
    server = _load_server()

    with tempfile.TemporaryDirectory() as tmpdir:
        state = _init(tmpdir)

        # Create a checkpoint
        from runtime.simflow_core.checkpoints import create_checkpoint
        create_checkpoint(
            workflow_id=state["workflow_id"],
            stage_id="computation",
            description="test checkpoint",
            project_root=tmpdir,
        )

        result = server.handle_request({
            "tool": "session_handoff",
            "params": {"project_root": tmpdir},
        })

        assert result["status"] == "success"
        assert result["data"]["latest_checkpoint"] is not None
        assert result["data"]["checkpoint_count"] == 1


def test_session_handoff_detects_stale_state():
    """session_handoff warns when workflow.json is stale vs latest checkpoint."""
    server = _load_server()

    with tempfile.TemporaryDirectory() as tmpdir:
        state = _init(tmpdir)

        # Make workflow.json stale by backdating it
        from runtime.simflow_core.state import read_state, write_state
        wf = read_state(project_root=tmpdir, state_file="workflow.json")
        wf["updated_at"] = "2026-01-01T00:00:00+00:00"
        write_state(wf, project_root=tmpdir, state_file="workflow.json")

        # Create a fresh checkpoint (which will touch_workflow and update timestamps)
        from runtime.simflow_core.checkpoints import create_checkpoint
        ckpt = create_checkpoint(
            workflow_id=state["workflow_id"],
            stage_id="computation",
            description="test checkpoint",
            project_root=tmpdir,
        )
        # touch_workflow updated workflow.json, so now backdate it again
        wf = read_state(project_root=tmpdir, state_file="workflow.json")
        wf["updated_at"] = "2026-01-01T00:00:00+00:00"
        write_state(wf, project_root=tmpdir, state_file="workflow.json")

        result = server.handle_request({
            "tool": "session_handoff",
            "params": {"project_root": tmpdir},
        })

        assert result["status"] == "success"
        warnings = result["data"]["warnings"]
        assert any("stale" in w.lower() for w in warnings), f"expected stale warning, got: {warnings}"


def test_session_handoff_warns_empty_gates_with_checkpoints():
    """session_handoff warns when checkpoints exist but gates.json is empty."""
    server = _load_server()

    with tempfile.TemporaryDirectory() as tmpdir:
        state = _init(tmpdir)

        # Create a checkpoint without any gates
        from runtime.simflow_core.checkpoints import create_checkpoint
        create_checkpoint(
            workflow_id=state["workflow_id"],
            stage_id="computation",
            description="test checkpoint",
            project_root=tmpdir,
        )

        result = server.handle_request({
            "tool": "session_handoff",
            "params": {"project_root": tmpdir},
        })

        assert result["status"] == "success"
        warnings = result["data"]["warnings"]
        assert any("gates.json is empty" in w for w in warnings)


def test_session_handoff_requires_project_root():
    """session_handoff requires project_root parameter."""
    server = _load_server()

    result = server.handle_request({
        "tool": "session_handoff",
        "params": {},
    })
    assert result["status"] == "error"
    assert "project_root" in result["message"]


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
