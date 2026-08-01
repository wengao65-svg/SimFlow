"""Tests for approval-bound HPC MCP file transfers."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from runtime.simflow_core.engagement import record_tool_call
from runtime.simflow_core.gates import record_gate_decision
from runtime.simflow_core.state import init_workflow


ROOT = Path(__file__).resolve().parents[2]
SERVER_DIR = ROOT / "mcp" / "servers" / "hpc"
TARGET = {"host": "fake-hpc", "user": "simflow", "port": 2222}


def _load_server():
    for name in [key for key in sys.modules if key == "connectors" or key.startswith("connectors.")]:
        del sys.modules[name]
    sys.path.insert(0, str(SERVER_DIR))
    sys.path.insert(0, str(ROOT / "mcp"))
    spec = importlib.util.spec_from_file_location("hpc_transfer_server", SERVER_DIR / "server.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _engage_and_approve(project_root: Path, server, direction: str, remote_dir: str, paths: list[str]):
    init_workflow("custom", "computation", project_root=str(project_root))
    record_tool_call("simflow_state/read_state", str(project_root))
    fingerprint = server.request_fingerprint(direction, remote_dir, paths, TARGET)
    decision = record_gate_decision(
        "hpc_transfer",
        "approved",
        {
            "direction": direction,
            "remote_dir": remote_dir,
            "paths": paths,
            "target": TARGET,
            "transfer_request_hash": fingerprint,
            "reason": "pytest transfer approval",
        },
        project_root=str(project_root),
        agent="pytest",
    )
    return decision


class _FakeConnector:
    host = "fake-hpc"

    def __init__(self, local_file: Path):
        self.local_file = local_file

    def upload_files(self, local_dir, remote_dir, files):
        assert local_dir.endswith("inputs")
        assert remote_dir == "/scratch/job"
        assert files == ["nested/input.txt"]
        return {"status": "success", "uploaded": 1, "files": files}

    def remote_file_manifest(self, remote_dir, files):
        manifest = {
            "algorithm": "sha256-path-size-content-v1",
            "file_count": 1,
            "total_size_bytes": self.local_file.stat().st_size,
            "files": [{"path": "nested/input.txt", "size_bytes": self.local_file.stat().st_size, "sha256": ""}],
        }
        import hashlib

        manifest["files"][0]["sha256"] = hashlib.sha256(self.local_file.read_bytes()).hexdigest()
        manifest["manifest_sha256"] = hashlib.sha256(
            json.dumps(manifest["files"], ensure_ascii=False, separators=(",", ":")).encode()
        ).hexdigest()
        return {"status": "success", "manifest": manifest}


def test_upload_requires_approval(tmp_path):
    server = _load_server()
    init_workflow("custom", "computation", project_root=str(tmp_path))
    record_tool_call("simflow_state/read_state", str(tmp_path))
    result = server.handle_request(
        {
            "tool": "upload",
            "params": {
                "project_root": str(tmp_path),
                "local_dir": "inputs",
                "remote_dir": "/scratch/job",
                "paths": ["nested/input.txt"],
                "target": TARGET,
            },
        }
    )
    assert result["status"] == "error"
    assert result["approval_required"] is True
    assert result["gate"] == "hpc_transfer"


def test_upload_registers_verified_manifest(tmp_path, monkeypatch):
    server = _load_server()
    local_file = tmp_path / "inputs" / "nested" / "input.txt"
    local_file.parent.mkdir(parents=True)
    local_file.write_text("input\n", encoding="utf-8")
    _engage_and_approve(tmp_path, server, "upload", "/scratch/job", ["nested/input.txt"])
    monkeypatch.setattr(server, "_get_connector", lambda scheduler, target=None: _FakeConnector(local_file))

    result = server.handle_request(
        {
            "tool": "upload",
            "params": {
                "project_root": str(tmp_path),
                "local_dir": "inputs",
                "remote_dir": "/scratch/job",
                "paths": ["nested/input.txt"],
                "target": TARGET,
                "gate_decision_id": server.get_gate_decisions("hpc_transfer", project_root=str(tmp_path))[-1]["decision_id"],
            },
        }
    )
    assert result["status"] == "success"
    assert result["data"]["transfer_status"] == "verified"
    assert result["data"]["artifact_id"].startswith("art_")
    report = json.loads((tmp_path / result["data"]["manifest_path"]).read_text(encoding="utf-8"))
    assert report["source_manifest"]["manifest_sha256"]
    assert report["remote_manifest"]["files"] == report["source_manifest"]["files"]
    assert report["target"] == TARGET


def test_upload_rejects_path_escape_before_approval(tmp_path):
    server = _load_server()
    init_workflow("custom", "computation", project_root=str(tmp_path))
    record_tool_call("simflow_state/read_state", str(tmp_path))
    result = server.handle_request(
        {
            "tool": "upload",
            "params": {
                "project_root": str(tmp_path),
                "local_dir": "inputs",
                "remote_dir": "/scratch/job",
                "paths": ["../secret.txt"],
                "target": TARGET,
            },
        }
    )
    assert result["status"] == "error"
    assert result["code"] == "transfer_validation_error"


def test_upload_rejects_target_mismatch(tmp_path):
    server = _load_server()
    local_file = tmp_path / "inputs" / "nested" / "input.txt"
    local_file.parent.mkdir(parents=True)
    local_file.write_text("input\n", encoding="utf-8")
    decision = _engage_and_approve(tmp_path, server, "upload", "/scratch/job", ["nested/input.txt"])
    result = server.handle_request(
        {
            "tool": "upload",
            "params": {
                "project_root": str(tmp_path),
                "local_dir": "inputs",
                "remote_dir": "/scratch/job",
                "paths": ["nested/input.txt"],
                "target": {"host": "other-hpc", "user": "simflow", "port": 2222},
                "gate_decision_id": decision["decision_id"],
            },
        }
    )
    assert result["status"] == "error"
    assert result["code"] == "transfer_approval_mismatch"


def test_upload_rejects_secret_fields_in_target(tmp_path):
    server = _load_server()
    init_workflow("custom", "computation", project_root=str(tmp_path))
    record_tool_call("simflow_state/read_state", str(tmp_path))
    result = server.handle_request(
        {
            "tool": "upload",
            "params": {
                "project_root": str(tmp_path),
                "local_dir": "inputs",
                "remote_dir": "/scratch/job",
                "paths": ["input.txt"],
                "target": {**TARGET, "password": "forbidden"},
            },
        }
    )
    assert result["status"] == "error"
    assert result["code"] == "transfer_validation_error"


def test_alias_target_is_valid_and_port_omission_changes_fingerprint():
    server = _load_server()
    alias_target = {"host": "hpc"}
    explicit_port = {"host": "hpc", "port": 22}

    assert server.normalize_target(alias_target) == alias_target
    assert server.request_fingerprint("upload", "/scratch/job", ["input.txt"], alias_target) != server.request_fingerprint(
        "upload", "/scratch/job", ["input.txt"], explicit_port
    )


def test_target_rejects_key_paths_and_ssh_options():
    server = _load_server()
    for field in ("key_file", "identity_file", "private_key", "ssh_options"):
        try:
            server.normalize_target({"host": "hpc", field: "forbidden"})
        except server.TransferValidationError:
            continue
        raise AssertionError(f"target unexpectedly accepted {field}")
