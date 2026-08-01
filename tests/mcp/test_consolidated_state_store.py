"""Tests for the v0.12 consolidated state/artifact/checkpoint MCP surface."""

import importlib.util
import sys
from pathlib import Path

from runtime.simflow_core.state import init_workflow


ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = ROOT / "mcp" / "servers" / "simflow_state"


def _load_state_server():
    for name in [key for key in sys.modules if key == "tools" or key.startswith("tools.")]:
        del sys.modules[name]
    sys.path.insert(0, str(STATE_DIR))
    spec = importlib.util.spec_from_file_location("consolidated_state_server", STATE_DIR / "server.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_state_server_exposes_consolidated_storage_tools():
    server = _load_state_server()
    assert {
        "register_artifact",
        "list_artifacts",
        "get_artifact",
        "create_checkpoint",
        "list_checkpoints",
        "restore_checkpoint",
    }.issubset(server.TOOLS)
    for name in (
        "register_artifact",
        "list_artifacts",
        "get_artifact",
        "create_checkpoint",
        "list_checkpoints",
        "restore_checkpoint",
    ):
        assert server.TOOL_SCHEMAS[name]["additionalProperties"] is False


def test_consolidated_artifact_and_checkpoint_flow(tmp_path):
    server = _load_state_server()
    workflow = init_workflow("custom", "computation", project_root=str(tmp_path))
    read = server.handle_request(
        {"tool": "read_state", "params": {"project_root": str(tmp_path), "file": "workflow.json"}}
    )
    assert read["status"] == "success"

    artifact_path = tmp_path / "result.json"
    artifact_path.write_text('{"ok": true}\n', encoding="utf-8")
    registered = server.handle_request(
        {
            "tool": "register_artifact",
            "params": {
                "project_root": str(tmp_path),
                "name": "result.json",
                "type": "report",
                "stage": "computation",
                "path": "result.json",
            },
        }
    )
    assert registered["status"] == "success"
    artifact_id = registered["data"]["artifact_id"]

    listed = server.handle_request(
        {"tool": "list_artifacts", "params": {"project_root": str(tmp_path)}}
    )
    fetched = server.handle_request(
        {"tool": "get_artifact", "params": {"project_root": str(tmp_path), "artifact_id": artifact_id}}
    )
    assert [item["artifact_id"] for item in listed["data"]] == [artifact_id]
    assert fetched["data"]["artifact_id"] == artifact_id

    created = server.handle_request(
        {
            "tool": "create_checkpoint",
            "params": {
                "project_root": str(tmp_path),
                "workflow_id": workflow["workflow_id"],
                "stage_id": "computation",
                "description": "consolidated MCP checkpoint",
            },
        }
    )
    assert created["status"] == "success"
    checkpoints = server.handle_request(
        {"tool": "list_checkpoints", "params": {"project_root": str(tmp_path)}}
    )
    assert checkpoints["data"][-1]["checkpoint_id"] == created["data"]["checkpoint_id"]


def test_consolidated_writes_still_require_engagement(tmp_path):
    server = _load_state_server()
    init_workflow("custom", "computation", project_root=str(tmp_path))
    result = server.handle_request(
        {
            "tool": "register_artifact",
            "params": {
                "project_root": str(tmp_path),
                "name": "planned",
                "type": "report",
                "stage": "computation",
            },
        }
    )
    assert result["status"] == "error"
    assert result["code"] == "skill_engagement_contract_violation"
