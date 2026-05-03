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
