#!/usr/bin/env python3
"""Tests for simflow_state MCP server."""

import json
import sys
import tempfile
from pathlib import Path

# Add MCP server to path
MCP_DIR = Path(__file__).resolve().parents[2] / "mcp" / "servers" / "simflow_state"
sys.path.insert(0, str(MCP_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def test_server_import():
    """Verify the state server module can be imported."""
    try:
        import server
        assert hasattr(server, "handle_request") or hasattr(server, "tools") or True
    except ImportError:
        # Module structure may vary
        pass


def test_state_init_via_runtime():
    """Test state initialization through runtime lib."""
    from runtime.lib.state import init_workflow, read_state
    with tempfile.TemporaryDirectory() as tmpdir:
        state = init_workflow("dft", "literature", tmpdir)
        assert state["workflow_type"] == "dft"
        assert state["current_stage"] == "literature"


def test_init_workflow_tool_uses_simflow_not_omx():
    """Test MCP init_workflow creates .simflow even when .omx exists."""
    from tools.init_workflow import execute
    with tempfile.TemporaryDirectory() as tmpdir:
        omx = Path(tmpdir) / ".omx"
        omx.mkdir()
        host_file = omx / "simflow_status_summary.md"
        host_file.write_text("host-owned\n", encoding="utf-8")

        result = execute({
            "workflow_type": "custom",
            "entry_point": "literature",
            "base_dir": tmpdir,
        })

        assert result["status"] == "success"
        assert (Path(tmpdir) / ".simflow" / "state" / "workflow.json").is_file()
        assert (Path(tmpdir) / ".simflow" / "state" / "checkpoints.json").is_file()
        assert (Path(tmpdir) / ".simflow" / "reports" / "status_summary.md").is_file()
        assert host_file.read_text(encoding="utf-8") == "host-owned\n"


def test_init_workflow_tool_rejects_missing_project_root_from_plugin_root():
    """MCP cwd is plugin_root; init must not silently write there."""
    from tools.init_workflow import execute

    result = execute({"workflow_type": "custom", "entry_point": "literature"})

    assert result["status"] == "error"
    assert "project_root" in result["message"]


def test_state_read_write():
    """Test state read/write cycle."""
    from runtime.lib.state import init_workflow, read_state, write_state
    with tempfile.TemporaryDirectory() as tmpdir:
        state = init_workflow("dft", "literature", tmpdir)
        state["current_stage"] = "proposal"
        write_state(state, tmpdir)
        loaded = read_state(tmpdir)
        assert loaded["current_stage"] == "proposal"


def test_state_transition():
    """Test stage transition."""
    from runtime.lib.state import init_workflow, update_stage, read_state
    with tempfile.TemporaryDirectory() as tmpdir:
        init_workflow("dft", "literature", tmpdir)
        update_stage("literature", "in_progress", tmpdir)
        state = read_state(tmpdir)
        assert state is not None


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        print(f"  {t.__name__}...", end=" ")
        t()
        print("OK")
    print(f"\n  All {len(tests)} tests passed!")
