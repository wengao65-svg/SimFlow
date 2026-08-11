"""Regression tests for read-only inspect and host-owned handoff behavior."""

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MCP_DIR = ROOT / "mcp" / "servers" / "simflow_state"


def _load_server():
    for name in [key for key in sys.modules if key == "tools" or key.startswith("tools.")]:
        del sys.modules[name]
    sys.path.insert(0, str(MCP_DIR))
    spec = importlib.util.spec_from_file_location("compact_state_read_tests", MCP_DIR / "server.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_inspect_does_not_bootstrap_or_write_state(tmp_path):
    server = _load_server()
    result = server.handle_request({"tool": "inspect", "params": {"project_root": str(tmp_path)}})
    assert result["status"] == "success"
    assert result["data"]["initialized"] is False
    assert not (tmp_path / ".simflow").exists()


def test_record_can_be_first_state_call(tmp_path):
    server = _load_server()
    result = server.handle_request({
        "tool": "record",
        "params": {"project_root": str(tmp_path), "kind": "note", "summary": "first call"},
    })
    assert result["status"] == "success"
    assert (tmp_path / ".simflow" / "records.jsonl").is_file()


def test_inspect_returns_current_summary_for_host_handoff(tmp_path):
    server = _load_server()
    server.handle_request({
        "tool": "record",
        "params": {
            "project_root": str(tmp_path),
            "kind": "milestone",
            "summary": "model validated",
            "goal": "evaluate production model",
            "next_action": "prepare immutable run plan",
        },
    })
    result = server.handle_request({"tool": "inspect", "params": {"project_root": str(tmp_path)}})
    current = result["data"]["project"]["current"]
    assert current["goal"] == "evaluate production model"
    assert current["next_action"] == "prepare immutable run plan"
    assert current["latest_milestone_id"].startswith("rec_")


def test_checkpoint_replaces_mandatory_session_handoff(tmp_path):
    server = _load_server()
    restart = tmp_path / "restart.dat"
    restart.write_text("restart\n", encoding="utf-8")
    checkpoint = server.handle_request({
        "tool": "checkpoint",
        "params": {
            "project_root": str(tmp_path),
            "summary": "recoverable boundary",
            "restart_refs": ["restart.dat"],
            "resume_command": "solver --restart restart.dat",
        },
    })
    assert checkpoint["status"] == "success"
    assert not (tmp_path / ".simflow" / "reports" / "session_handoff.md").exists()
    inspected = server.handle_request({"tool": "inspect", "params": {"project_root": str(tmp_path)}})
    assert inspected["data"]["project"]["current"]["latest_checkpoint_id"] == checkpoint["data"]["checkpoint_id"]


def test_legacy_state_is_reported_without_auto_migration(tmp_path):
    legacy = tmp_path / ".simflow" / "state"
    legacy.mkdir(parents=True)
    workflow = legacy / "workflow.json"
    workflow.write_text('{"workflow_id":"wf_old"}\n', encoding="utf-8")
    server = _load_server()
    result = server.handle_request({"tool": "inspect", "params": {"project_root": str(tmp_path)}})
    assert result["data"]["legacy"]["detected"] is True
    assert workflow.read_text(encoding="utf-8") == '{"workflow_id":"wf_old"}\n'
    assert not (tmp_path / ".simflow" / "project.json").exists()


def test_all_public_tools_require_explicit_project_root():
    server = _load_server()
    for tool in ("inspect", "record", "checkpoint", "recover"):
        result = server.handle_request({"tool": tool, "params": {}})
        assert result["status"] == "error"
        assert "project_root" in result["message"]
