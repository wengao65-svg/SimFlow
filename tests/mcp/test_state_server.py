#!/usr/bin/env python3
"""Tests for the compact simflow_state MCP server."""

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MCP_DIR = ROOT / "mcp" / "servers" / "simflow_state"
sys.path.insert(0, str(MCP_DIR))
sys.path.insert(0, str(ROOT))


def _load_state_server():
    for name in [key for key in sys.modules if key == "tools" or key.startswith("tools.")]:
        del sys.modules[name]
    spec = importlib.util.spec_from_file_location("compact_state_server", MCP_DIR / "server.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_server_exposes_exactly_four_composite_tools():
    from mcp.shared.stdio_server import _list_tools

    server = _load_state_server()
    assert set(server.TOOLS) == {"inspect", "record", "checkpoint", "recover"}
    listed = _list_tools(server.TOOLS, server.TOOL_DESCRIPTIONS, server.TOOL_SCHEMAS)
    schemas = {item["name"]: item["inputSchema"] for item in listed}
    assert schemas["inspect"]["required"] == ["project_root"]
    assert len(schemas["record"]["oneOf"]) == 7
    assert schemas["record"]["oneOf"][0]["required"] == ["project_root", "kind", "summary"]
    assert {branch["properties"]["entry_type"]["const"] for branch in schemas["record"]["oneOf"][1:]} == {
        "experiment", "attempt", "observation", "decision", "material_action", "recovery",
    }
    assert schemas["checkpoint"]["required"] == ["project_root", "summary"]
    assert schemas["recover"]["required"] == ["project_root"]
    assert all(schema["additionalProperties"] is False for schema in schemas.values())
    assert "migration" in schemas["inspect"]["properties"]["kind"]["enum"]
    assert "migration" in schemas["record"]["properties"]["kind"]["enum"]


def test_experiment_record_schema_is_separate_from_operational_kinds(tmp_path):
    server = _load_state_server()
    mixed = server.handle_request({
        "tool": "record",
        "params": {
            "project_root": str(tmp_path),
            "channel": "experiment",
            "kind": "note",
            "entry_type": "experiment",
            "action": "create",
            "summary": "invalid mixed record",
            "payload": {"title": "Question", "research_question": "Why?", "scope_paths": ["."]},
        },
    })
    wrong_payload = server.handle_request({
        "tool": "record",
        "params": {
            "project_root": str(tmp_path),
            "channel": "experiment",
            "entry_type": "attempt",
            "action": "define",
            "summary": "invalid attempt",
            "experiment_id": "exp_123456789abc",
            "payload": {"title": "not an attempt field"},
        },
    })

    assert mixed["status"] == "error"
    assert "Unsupported experiment record fields" in mixed["message"]
    assert wrong_payload["status"] == "error"
    assert "Unsupported attempt payload fields" in wrong_payload["message"]


def test_create_inspect_and_append_experiment_memory(tmp_path):
    server = _load_state_server()
    scope = tmp_path / "stage6_NEP" / "NEPv3"
    scope.mkdir(parents=True)
    created = server.handle_request({
        "tool": "record",
        "params": {
            "project_root": str(tmp_path),
            "channel": "experiment",
            "entry_type": "experiment",
            "action": "create",
            "summary": "Define the high-temperature dataset question",
            "payload": {
                "title": "NEPv3 high-temperature dataset",
                "research_question": "Should frames at or above 400 K enter NEPv3?",
                "scope_paths": ["stage6_NEP/NEPv3"],
                "tags": ["nep", "dataset"],
            },
        },
    })
    experiment_id = created["data"]["experiment_id"]
    appended = server.handle_request({
        "tool": "record",
        "params": {
            "project_root": str(tmp_path),
            "channel": "experiment",
            "entry_type": "observation",
            "action": "record",
            "summary": "Frames at or above 400 K were excluded",
            "experiment_id": experiment_id,
            "payload": {"details": {"criterion": "temperature >= 400 K"}, "next_action": "train NEPv3"},
        },
    })
    inspected = server.handle_request({
        "tool": "inspect",
        "params": {
            "project_root": str(tmp_path),
            "working_directory": str(scope),
            "query": "NEPv3 400 K dataset",
        },
    })

    assert created["status"] == appended["status"] == inspected["status"] == "success"
    assert inspected["data"]["experiment_memory"]["selected_experiment_id"] == experiment_id
    assert inspected["data"]["experiment_memory"]["entries"][-1]["entry_type"] == "observation"
    assert inspected["data"]["project"]["current"]["next_action"] == "train NEPv3"
    assert (tmp_path / ".simflow" / "experiments" / "index.md").is_file()


def test_record_initializes_compact_store_without_engagement(tmp_path):
    server = _load_state_server()
    result = server.handle_request({
        "tool": "record",
        "params": {
            "project_root": str(tmp_path),
            "kind": "run",
            "summary": "Prepared diagnostic run",
            "status": "prepared",
            "goal": "check convergence",
            "next_action": "submit after approval",
        },
    })

    assert result["status"] == "success"
    assert result["data"]["run_id"].startswith("run_")
    assert (tmp_path / ".simflow" / "project.json").is_file()
    assert (tmp_path / ".simflow" / "records.jsonl").is_file()
    assert not (tmp_path / ".simflow" / "state").exists()
    assert not (tmp_path / ".simflow" / ".records.lock").exists()


def test_inspect_is_read_only_for_uninitialized_project(tmp_path):
    server = _load_state_server()
    result = server.handle_request({"tool": "inspect", "params": {"project_root": str(tmp_path)}})

    assert result["status"] == "success"
    assert result["data"]["initialized"] is False
    assert result["data"]["records"] == []
    assert not (tmp_path / ".simflow").exists()


def test_record_groups_logical_artifacts_and_redacts_secrets(tmp_path):
    server = _load_state_server()
    output = tmp_path / "run" / "summary.json"
    output.parent.mkdir()
    output.write_text('{"ok": true}\n', encoding="utf-8")
    result = server.handle_request({
        "tool": "record",
        "params": {
            "project_root": str(tmp_path),
            "kind": "artifact",
            "summary": "Run deliverables",
            "artifacts": [{"path": "run/summary.json", "role": "run_manifest"}],
            "details": {
                "password": "secret",
                "command": "curl -H 'Authorization: Bearer abc.def' example.invalid",
                "potcar_dataset": "PAW_PBE/Fe_pv",
                "potcar_content": "restricted body",
            },
        },
    })

    record = result["data"]
    assert record["artifacts"][0]["sha256"]
    assert record["details"]["password"] == "[REDACTED]"
    assert "Bearer [REDACTED]" in record["details"]["command"]
    assert record["details"]["potcar_dataset"] == "PAW_PBE/Fe_pv"
    assert record["details"]["potcar_content"] == "[REDACTED]"
    persisted = json.loads((tmp_path / ".simflow" / "records.jsonl").read_text(encoding="utf-8"))
    assert persisted["record_id"] == record["record_id"]


def test_checkpoint_is_compact_and_recover_validates_hashes(tmp_path):
    server = _load_state_server()
    restart = tmp_path / "run" / "restart.wfn"
    restart.parent.mkdir()
    restart.write_text("restart\n", encoding="utf-8")
    run = server.handle_request({
        "tool": "record",
        "params": {
            "project_root": str(tmp_path),
            "kind": "run",
            "summary": "AIMD paused",
            "status": "paused",
        },
    })["data"]
    created = server.handle_request({
        "tool": "checkpoint",
        "params": {
            "project_root": str(tmp_path),
            "summary": "Resume AIMD",
            "run_id": run["run_id"],
            "restart_refs": ["run/restart.wfn"],
            "resume_command": "cp2k.psmp -i restart.inp",
        },
    })

    checkpoint = created["data"]
    assert "state_snapshot" not in checkpoint
    assert "lineage_snapshot" not in checkpoint
    recovered = server.handle_request({
        "tool": "recover",
        "params": {"project_root": str(tmp_path), "checkpoint_id": checkpoint["checkpoint_id"]},
    })
    assert recovered["status"] == "success"
    assert recovered["data"]["ready"] is True

    restart.write_text("changed\n", encoding="utf-8")
    mismatched = server.handle_request({
        "tool": "recover",
        "params": {"project_root": str(tmp_path), "checkpoint_id": checkpoint["checkpoint_id"]},
    })
    assert mismatched["data"]["ready"] is False
    assert mismatched["data"]["issues"][0]["status"] == "hash_mismatch"


def test_inspect_reports_legacy_state_without_rewriting_it(tmp_path):
    legacy = tmp_path / ".simflow" / "state"
    legacy.mkdir(parents=True)
    artifacts = legacy / "artifacts.json"
    artifacts.write_text('[{"artifact_id": "art_old"}]\n', encoding="utf-8")

    server = _load_state_server()
    result = server.handle_request({"tool": "inspect", "params": {"project_root": str(tmp_path)}})

    assert result["data"]["legacy"]["detected"] is True
    assert result["data"]["legacy"]["counts"]["artifacts"] == 1
    assert artifacts.read_text(encoding="utf-8") == '[{"artifact_id": "art_old"}]\n'
    assert not (tmp_path / ".simflow" / "project.json").exists()


def test_migration_is_confirmed_by_inspected_hash_and_is_idempotent(tmp_path):
    legacy = tmp_path / ".simflow" / "state"
    legacy.mkdir(parents=True)
    workflow = legacy / "workflow.json"
    workflow.write_text('{"workflow_id": "wf_old"}\n', encoding="utf-8")
    original = workflow.read_bytes()
    server = _load_state_server()

    inspected = server.handle_request({"tool": "inspect", "params": {"project_root": str(tmp_path)}})
    report_hash = inspected["data"]["migration"]["migration_report_hash"]
    params = {
        "project_root": str(tmp_path),
        "kind": "migration",
        "summary": "Index legacy state",
        "migration_report_hash": report_hash,
        "confirm_migration": True,
    }
    first = server.handle_request({"tool": "record", "params": params})
    second = server.handle_request({"tool": "record", "params": params})

    assert first["status"] == "success"
    assert first["data"]["status"] == "applied"
    assert second["data"]["status"] == "already_applied"
    assert workflow.read_bytes() == original
    records = (tmp_path / ".simflow" / "records.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(records) == 1


def test_unknown_tool_returns_error():
    server = _load_state_server()
    result = server.handle_request({"tool": "read_state", "params": {}})
    assert result == {"status": "error", "message": "Unknown tool: read_state"}
