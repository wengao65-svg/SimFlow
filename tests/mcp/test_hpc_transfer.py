"""Tests for immutable-plan HPC transfers."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

from runtime.simflow_core.gates import record_gate_decision
from runtime.simflow_core.records import list_project_records


ROOT = Path(__file__).resolve().parents[2]
SERVER_DIR = ROOT / "mcp" / "servers" / "hpc"
TARGET = {"host": "fake-hpc", "user": "simflow", "port": 2222}


def _load_server():
    for name in [key for key in sys.modules if key == "connectors" or key.startswith("connectors.")]:
        del sys.modules[name]
    sys.path.insert(0, str(SERVER_DIR))
    spec = importlib.util.spec_from_file_location("hpc_transfer_server", SERVER_DIR / "server.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _plan_upload(project_root: Path, server, *, paths: list[str] | None = None) -> dict:
    inputs = project_root / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    script = inputs / "job.sh"
    data = inputs / "input.txt"
    script.write_text("#!/bin/bash\necho remote\n", encoding="utf-8")
    script.chmod(0o755)
    data.write_text("input\n", encoding="utf-8")
    transfer_paths = paths or ["job.sh", "input.txt"]
    result = server.handle_request({
        "tool": "plan",
        "params": {
            "project_root": str(project_root),
            "script_path": "inputs/job.sh",
            "input_paths": ["inputs/job.sh", "inputs/input.txt"],
            "scheduler": "ssh",
            "target": TARGET,
            "remote_workdir": "/scratch/job",
            "transfer": {
                "direction": "upload",
                "local_dir": "inputs",
                "remote_dir": "/scratch/job",
                "paths": transfer_paths,
            },
            "destructive_scope": ["remote:/scratch/job"],
        },
    })
    assert result["status"] == "success", result
    return result["data"]


def _approve(project_root: Path, run_plan_hash: str, gate: str = "hpc_submit") -> dict:
    return record_gate_decision(
        gate,
        "approved",
        {"run_plan_hash": run_plan_hash, "reason": "pytest transfer approval"},
        project_root=str(project_root),
        agent="pytest",
    )


class _FakeUploadConnector:
    def __init__(self, local_root: Path):
        self.local_root = local_root

    def upload_files(self, local_dir, remote_dir, files):
        assert Path(local_dir) == self.local_root
        assert remote_dir == "/scratch/job"
        return {"status": "success", "uploaded": len(files), "files": files}

    def remote_file_manifest(self, remote_dir, files):
        entries = []
        for rel in files:
            path = self.local_root / rel
            entries.append({
                "path": rel,
                "size_bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            })
        entries.sort(key=lambda item: item["path"])
        manifest = {
            "algorithm": "sha256-path-size-content-v1",
            "file_count": len(entries),
            "total_size_bytes": sum(item["size_bytes"] for item in entries),
            "files": entries,
            "manifest_sha256": hashlib.sha256(
                json.dumps(entries, ensure_ascii=False, separators=(",", ":")).encode()
            ).hexdigest(),
        }
        return {"status": "success", "manifest": manifest}


def test_transfer_requires_plan_bound_approval(tmp_path):
    server = _load_server()
    plan = _plan_upload(tmp_path, server)
    result = server.handle_request({
        "tool": "transfer",
        "params": {
            "project_root": str(tmp_path),
            "run_plan_hash": plan["run_plan_hash"],
            "direction": "upload",
        },
    })

    assert result["status"] == "error"
    assert result["approval_required"] is True
    assert result["run_plan_hash"] == plan["run_plan_hash"]


def test_upload_reuses_submit_approval_and_records_one_run(tmp_path, monkeypatch):
    server = _load_server()
    plan = _plan_upload(tmp_path, server)
    decision = _approve(tmp_path, plan["run_plan_hash"])
    monkeypatch.setattr(server, "_get_connector", lambda scheduler, target=None: _FakeUploadConnector(tmp_path / "inputs"))
    result = server.handle_request({
        "tool": "transfer",
        "params": {
            "project_root": str(tmp_path),
            "run_plan_hash": plan["run_plan_hash"],
            "direction": "upload",
            "gate_decision_id": decision["decision_id"],
        },
    })

    assert result["status"] == "success"
    assert result["data"]["transfer_status"] == "verified"
    assert result["data"]["report"]["run_plan_hash"] == plan["run_plan_hash"]
    records = list_project_records(str(tmp_path), kind="run")
    assert len(records) == 1
    assert records[0]["details"]["operation"] == "transfer"
    assert records[0]["details"]["run_plan_hash"] == plan["run_plan_hash"]


def test_transfer_accepts_dedicated_transfer_gate(tmp_path, monkeypatch):
    server = _load_server()
    plan = _plan_upload(tmp_path, server)
    decision = _approve(tmp_path, plan["run_plan_hash"], gate="hpc_transfer")
    monkeypatch.setattr(server, "_get_connector", lambda scheduler, target=None: _FakeUploadConnector(tmp_path / "inputs"))
    result = server.handle_request({
        "tool": "transfer",
        "params": {
            "project_root": str(tmp_path),
            "run_plan_hash": plan["run_plan_hash"],
            "direction": "upload",
            "gate_decision_id": decision["decision_id"],
        },
    })
    assert result["status"] == "success"


def test_direction_must_match_run_plan(tmp_path):
    server = _load_server()
    plan = _plan_upload(tmp_path, server)
    decision = _approve(tmp_path, plan["run_plan_hash"])
    result = server.handle_request({
        "tool": "transfer",
        "params": {
            "project_root": str(tmp_path),
            "run_plan_hash": plan["run_plan_hash"],
            "direction": "download",
            "gate_decision_id": decision["decision_id"],
        },
    })
    assert result["status"] == "error"
    assert result["code"] == "run_plan_transfer_mismatch"


def test_changed_transfer_input_invalidates_approval(tmp_path):
    server = _load_server()
    plan = _plan_upload(tmp_path, server)
    decision = _approve(tmp_path, plan["run_plan_hash"])
    (tmp_path / "inputs" / "input.txt").write_text("changed\n", encoding="utf-8")
    result = server.handle_request({
        "tool": "transfer",
        "params": {
            "project_root": str(tmp_path),
            "run_plan_hash": plan["run_plan_hash"],
            "direction": "upload",
            "gate_decision_id": decision["decision_id"],
        },
    })
    assert result["status"] == "error"
    assert result["code"] == "run_plan_stale"


def test_potcar_is_hashed_and_never_serialized(tmp_path, monkeypatch):
    server = _load_server()
    marker = "PRIVATE_POTCAR_TRANSFER_BODY"
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    (inputs / "job.sh").write_text("#!/bin/bash\necho remote\n", encoding="utf-8")
    (inputs / "job.sh").chmod(0o755)
    potcar = inputs / "POTCAR"
    potcar.write_text(f"PAW_PBE Si\n{marker}\n", encoding="utf-8")
    planned = server.handle_request({
        "tool": "plan",
        "params": {
            "project_root": str(tmp_path),
            "script_path": "inputs/job.sh",
            "input_paths": ["inputs/job.sh", "inputs/POTCAR"],
            "scheduler": "ssh",
            "target": TARGET,
            "remote_workdir": "/scratch/job",
            "transfer": {
                "direction": "upload",
                "local_dir": "inputs",
                "remote_dir": "/scratch/job",
                "paths": ["job.sh", "POTCAR"],
            },
        },
    })["data"]
    assert planned["restricted_files"][0]["classification"] == "restricted_licensed_vasp_potcar"
    assert marker not in json.dumps(planned)
    decision = _approve(tmp_path, planned["run_plan_hash"])
    monkeypatch.setattr(server, "_get_connector", lambda scheduler, target=None: _FakeUploadConnector(inputs))
    result = server.handle_request({
        "tool": "transfer",
        "params": {
            "project_root": str(tmp_path),
            "run_plan_hash": planned["run_plan_hash"],
            "direction": "upload",
            "gate_decision_id": decision["decision_id"],
        },
    })
    assert result["status"] == "success"
    assert marker not in json.dumps(result)
    assert marker not in (tmp_path / result["data"]["manifest_path"]).read_text(encoding="utf-8")


def test_plan_rejects_transfer_path_escape(tmp_path):
    server = _load_server()
    _plan_upload(tmp_path, server)
    result = server.handle_request({
        "tool": "plan",
        "params": {
            "project_root": str(tmp_path),
            "script_path": "inputs/job.sh",
            "input_paths": ["inputs/input.txt"],
            "scheduler": "ssh",
            "target": TARGET,
            "remote_workdir": "/scratch/job",
            "transfer": {
                "direction": "upload",
                "local_dir": "inputs",
                "remote_dir": "/scratch/job",
                "paths": ["../secret.txt"],
            },
        },
    })
    assert result["status"] == "error"
    assert result["code"] == "run_plan_invalid"


def test_target_rejects_secret_fields():
    server = _load_server()
    try:
        server.normalize_target({**TARGET, "password": "forbidden"})
    except server.TransferValidationError:
        return
    raise AssertionError("target unexpectedly accepted a password")


def test_target_alias_and_explicit_port_are_distinct():
    server = _load_server()
    assert server.normalize_target({"host": "hpc"}) != server.normalize_target({"host": "hpc", "port": 22})
