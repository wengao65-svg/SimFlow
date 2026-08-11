"""Regression tests for removal of the state engagement ceremony."""

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MCP_STATE_DIR = ROOT / "mcp" / "servers" / "simflow_state"


def _load_state_server():
    for name in [key for key in sys.modules if key == "tools" or key.startswith("tools.")]:
        del sys.modules[name]
    sys.path.insert(0, str(MCP_STATE_DIR))
    spec = importlib.util.spec_from_file_location("state_server_without_engagement", MCP_STATE_DIR / "server.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_state_write_does_not_require_read_first(tmp_path):
    server = _load_state_server()
    result = server.handle_request({
        "tool": "record",
        "params": {
            "project_root": str(tmp_path),
            "kind": "milestone",
            "summary": "direct write",
        },
    })
    assert result["status"] == "success"


def test_compact_state_does_not_create_engagement_log(tmp_path):
    server = _load_state_server()
    server.handle_request({
        "tool": "record",
        "params": {
            "project_root": str(tmp_path),
            "kind": "note",
            "summary": "no engagement log",
        },
    })
    assert not (tmp_path / ".simflow" / "state" / "mcp_engagement_log.jsonl").exists()


def test_activity_and_experiment_tools_are_not_public(tmp_path):
    server = _load_state_server()
    for tool in ("project_reentry", "begin_experiment", "start_activity", "finish_activity"):
        result = server.handle_request({"tool": tool, "params": {"project_root": str(tmp_path)}})
        assert result["status"] == "error"
        assert result["message"] == f"Unknown tool: {tool}"
