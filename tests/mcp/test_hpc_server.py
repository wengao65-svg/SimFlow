#!/usr/bin/env python3
"""Integration tests for the compact HPC MCP surface."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from runtime.simflow_core.gates import record_gate_decision
from runtime.simflow_core.records import list_project_records, record_event


SERVER_DIR = Path(__file__).resolve().parents[2] / "mcp" / "servers" / "hpc"


def _load_server():
    for name in [key for key in sys.modules if key == "connectors" or key.startswith("connectors.")]:
        del sys.modules[name]
    sys.path.insert(0, str(SERVER_DIR))
    spec = importlib.util.spec_from_file_location("hpc_server", SERVER_DIR / "server.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make_local_files(root: Path) -> tuple[Path, Path]:
    script = root / "job.sh"
    input_file = root / "input.dat"
    script.write_text("#!/bin/bash\necho local-ok\n", encoding="utf-8")
    script.chmod(0o755)
    input_file.write_text("input\n", encoding="utf-8")
    return script, input_file


def _plan_local(server, root: Path) -> dict:
    _make_local_files(root)
    result = server.handle_request({
        "tool": "plan",
        "params": {
            "project_root": str(root),
            "script_path": "job.sh",
            "input_paths": ["input.dat"],
            "scheduler": "local",
            "resources": {"nodes": 1, "ntasks": 1, "walltime": "00:05:00"},
        },
    })
    assert result["status"] == "success", result
    return result["data"]


def _approve(root: Path, run_plan_hash: str, gate: str = "hpc_submit") -> dict:
    return record_gate_decision(
        gate,
        "approved",
        {"run_plan_hash": run_plan_hash, "reason": "pytest immutable plan approval"},
        project_root=str(root),
        agent="pytest",
    )


def test_tools_surface_is_exactly_four_composite_actions():
    from mcp.shared.stdio_server import _list_tools

    server = _load_server()
    listed = _list_tools(server.TOOLS, server.TOOL_DESCRIPTIONS, server.TOOL_SCHEMAS)
    schemas = {tool["name"]: tool["inputSchema"] for tool in listed}

    assert set(schemas) == {"plan", "transfer", "submit", "status"}
    assert set(schemas["plan"]["required"]) == {"project_root", "script_path", "input_paths"}
    assert set(schemas["transfer"]["required"]) == {"project_root", "run_plan_hash", "direction"}
    assert set(schemas["submit"]["required"]) == {"project_root", "run_plan_hash"}
    for removed in ("dry_run_evidence", "script_hash", "input_artifact_hash", "session_context_id"):
        assert removed not in schemas["submit"]["properties"]


def test_plan_validates_existing_script_and_persists_hash(tmp_path):
    server = _load_server()
    plan = _plan_local(server, tmp_path)

    assert len(plan["run_plan_hash"]) == 64
    assert plan["scheduler"] == "local"
    assert plan["script"]["path"] == "job.sh"
    assert plan["inputs"]["file_count"] == 2
    assert plan["resources"]["nodes"] == 1
    assert (tmp_path / plan["plan_path"]).is_file()


def test_plan_can_generate_and_validate_slurm_script(tmp_path):
    server = _load_server()
    (tmp_path / "INCAR").write_text("SYSTEM = test\n", encoding="utf-8")
    result = server.handle_request({
        "tool": "plan",
        "params": {
            "project_root": str(tmp_path),
            "script_path": "submit.sh",
            "input_paths": ["INCAR"],
            "scheduler": "slurm",
            "generate": {
                "job_name": "si_relax",
                "executable": "vasp_std",
                "nodes": 2,
                "ntasks": 32,
                "walltime": "04:00:00",
            },
        },
    })

    assert result["status"] == "success", result
    assert result["data"]["script_generated"] is True
    assert "#SBATCH" in (tmp_path / "submit.sh").read_text(encoding="utf-8")
    assert result["data"]["resources"] == {"nodes": 2, "ntasks": 32, "walltime": "04:00:00"}


def test_plan_fails_closed_on_credential_pattern(tmp_path):
    server = _load_server()
    script, input_file = _make_local_files(tmp_path)
    input_file.write_text("api_key=do-not-store\n", encoding="utf-8")
    result = server.handle_request({
        "tool": "plan",
        "params": {
            "project_root": str(tmp_path),
            "script_path": script.name,
            "input_paths": [input_file.name],
            "scheduler": "local",
        },
    })

    assert result["status"] == "error"
    assert result["data"]["credential_scan"]["status"] == "fail"
    assert "do-not-store" not in str(result)


def test_submit_requires_approval_bound_to_run_plan(tmp_path):
    server = _load_server()
    plan = _plan_local(server, tmp_path)
    result = server.handle_request({
        "tool": "submit",
        "params": {"project_root": str(tmp_path), "run_plan_hash": plan["run_plan_hash"]},
    })

    assert result["status"] == "error"
    assert result["approval_required"] is True
    assert result["run_plan_hash"] == plan["run_plan_hash"]


def test_submit_rejects_approval_for_different_plan(tmp_path):
    server = _load_server()
    plan = _plan_local(server, tmp_path)
    decision = _approve(tmp_path, "0" * 64)
    result = server.handle_request({
        "tool": "submit",
        "params": {
            "project_root": str(tmp_path),
            "run_plan_hash": plan["run_plan_hash"],
            "gate_decision_id": decision["decision_id"],
        },
    })

    assert result["status"] == "error"
    assert result["code"] == "run_plan_approval_mismatch"


def test_local_submit_executes_and_records_one_compact_run(tmp_path):
    server = _load_server()
    plan = _plan_local(server, tmp_path)
    decision = _approve(tmp_path, plan["run_plan_hash"])
    result = server.handle_request({
        "tool": "submit",
        "params": {
            "project_root": str(tmp_path),
            "run_plan_hash": plan["run_plan_hash"],
            "gate_decision_id": decision["decision_id"],
        },
    })

    assert result["status"] == "success"
    assert "local-ok" in result["stdout"]
    assert result["run_plan_hash"] == plan["run_plan_hash"]
    records = list_project_records(str(tmp_path), kind="run")
    assert len(records) == 1
    assert records[0]["details"]["operation"] == "submit"
    assert records[0]["details"]["run_plan_hash"] == plan["run_plan_hash"]
    assert not (tmp_path / ".simflow" / "state" / "jobs.json").exists()


def test_public_compact_approval_record_authorizes_submit(tmp_path):
    server = _load_server()
    plan = _plan_local(server, tmp_path)
    approval = record_event(
        str(tmp_path),
        kind="approval",
        summary="Approve immutable local run",
        status="approved",
        details={
            "gate": "hpc_submit",
            "conditions": {"run_plan_hash": plan["run_plan_hash"]},
            "agent": "pytest",
        },
    )
    result = server.handle_request({
        "tool": "submit",
        "params": {
            "project_root": str(tmp_path),
            "run_plan_hash": plan["run_plan_hash"],
            "gate_decision_id": approval["record_id"],
        },
    })

    assert result["status"] == "success"
    assert result["gate_decision_id"] == approval["record_id"]


def test_unchanged_retry_reuses_same_approval(tmp_path):
    server = _load_server()
    plan = _plan_local(server, tmp_path)
    decision = _approve(tmp_path, plan["run_plan_hash"])
    request = {
        "tool": "submit",
        "params": {
            "project_root": str(tmp_path),
            "run_plan_hash": plan["run_plan_hash"],
            "gate_decision_id": decision["decision_id"],
        },
    }

    first = server.handle_request(request)
    second = server.handle_request(request)

    assert first["status"] == second["status"] == "success"
    assert len(list_project_records(str(tmp_path), kind="run")) == 2


def test_changed_input_invalidates_prior_approval(tmp_path):
    server = _load_server()
    plan = _plan_local(server, tmp_path)
    decision = _approve(tmp_path, plan["run_plan_hash"])
    (tmp_path / "input.dat").write_text("changed\n", encoding="utf-8")
    result = server.handle_request({
        "tool": "submit",
        "params": {
            "project_root": str(tmp_path),
            "run_plan_hash": plan["run_plan_hash"],
            "gate_decision_id": decision["decision_id"],
        },
    })

    assert result["status"] == "error"
    assert result["code"] == "run_plan_stale"
    assert result["approval_required"] is True


def test_resources_and_target_change_run_plan_hash(tmp_path):
    server = _load_server()
    _make_local_files(tmp_path)
    common = {
        "project_root": str(tmp_path),
        "script_path": "job.sh",
        "input_paths": ["input.dat"],
        "scheduler": "ssh",
        "remote_workdir": "/scratch/job",
        "transfer": {"direction": "upload", "remote_dir": "/scratch/job"},
    }
    first = server.handle_request({"tool": "plan", "params": {
        **common, "target": {"host": "hpc-a"}, "resources": {"nodes": 1},
    }})["data"]
    second = server.handle_request({"tool": "plan", "params": {
        **common, "target": {"host": "hpc-b"}, "resources": {"nodes": 1},
    }})["data"]
    third = server.handle_request({"tool": "plan", "params": {
        **common, "target": {"host": "hpc-a"}, "resources": {"nodes": 2},
    }})["data"]

    assert len({first["run_plan_hash"], second["run_plan_hash"], third["run_plan_hash"]}) == 3


def test_ssh_submit_requires_verified_transfer_manifest(tmp_path):
    server = _load_server()
    _make_local_files(tmp_path)
    planned = server.handle_request({
        "tool": "plan",
        "params": {
            "project_root": str(tmp_path),
            "script_path": "job.sh",
            "input_paths": ["input.dat"],
            "scheduler": "ssh",
            "target": {"host": "hpc"},
            "remote_workdir": "/scratch/job",
            "transfer": {"direction": "upload", "remote_dir": "/scratch/job"},
        },
    })["data"]
    decision = _approve(tmp_path, planned["run_plan_hash"])
    result = server.handle_request({
        "tool": "submit",
        "params": {
            "project_root": str(tmp_path),
            "run_plan_hash": planned["run_plan_hash"],
            "gate_decision_id": decision["decision_id"],
        },
    })

    assert result["status"] == "error"
    assert result["code"] == "transfer_manifest_required"


def test_status_requires_target_for_ssh():
    server = _load_server()
    result = server.handle_request({"tool": "status", "params": {"job_id": "123", "scheduler": "ssh"}})
    assert result["status"] == "error"
    assert result["code"] == "target_required"


def test_unknown_tool_is_rejected():
    server = _load_server()
    result = server.handle_request({"tool": "dry_run", "params": {}})
    assert result["status"] == "error"
    assert result["code"] == "UNKNOWN_TOOL"
    assert result["message"] == "Unknown tool: dry_run"
