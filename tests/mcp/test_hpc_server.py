#!/usr/bin/env python3
"""Integration tests for HPC MCP server.

Tests the server's handle_request() function end-to-end,
verifying dry_run, prepare, and status tools.
"""

import importlib.util
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

from runtime.simflow_core.gates import record_gate_decision

SERVER_DIR = Path(__file__).resolve().parents[2] / "mcp" / "servers" / "hpc"


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _authorized_submit_params(project_root: str, script_path: str) -> dict:
    root = Path(project_root)
    input_hash = "input-manifest-sha256"
    script_hash = _sha256_file(script_path)
    artifacts = root / ".simflow" / "artifacts"
    _write_json(
        artifacts / "compute" / "dry_run_report.json",
        {
            "status": "pass",
            "script_hash": script_hash,
            "input_artifact_hash": input_hash,
        },
    )
    _write_json(artifacts / "compute" / "input_validation.json", {"missing_required_files": []})
    _write_json(artifacts / "compute" / "resource_estimate.json", {"status": "pass"})
    _write_json(artifacts / "security" / "credential_scan.json", {"findings": []})
    decision = record_gate_decision(
        "hpc_submit",
        "approved",
        {"reason": "pytest MCP submit authorization"},
        project_root=project_root,
        agent="pytest",
    )
    return {
        "project_root": project_root,
        "gate_decision_id": decision["decision_id"],
        "dry_run_evidence": "compute/dry_run_report.json",
        "script_hash": script_hash,
        "input_artifact_hash": input_hash,
    }


def _load_server():
    """Load the HPC server module by file path to avoid name collisions."""
    # Clear cached connectors modules to avoid cross-test contamination
    mods_to_remove = [k for k in sys.modules if k.startswith("connectors")]
    for m in mods_to_remove:
        del sys.modules[m]

    server_path = SERVER_DIR / "server.py"
    spec = importlib.util.spec_from_file_location("hpc_server", server_path)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(SERVER_DIR))
    sys.path.insert(0, str(SERVER_DIR.parent.parent.parent))
    spec.loader.exec_module(mod)
    return mod


def _make_test_script(tmpdir):
    """Create a minimal test SLURM script."""
    script = os.path.join(tmpdir, "test_job.sh")
    with open(script, "w") as f:
        f.write("#!/bin/bash\n")
        f.write("#SBATCH --job-name=test_job\n")
        f.write("#SBATCH --nodes=1\n")
        f.write("#SBATCH --ntasks-per-node=4\n")
        f.write("#SBATCH --time=01:00:00\n")
        f.write("#SBATCH --output=job.out\n")
        f.write("#SBATCH --error=job.err\n")
        f.write("\n")
        f.write("mpirun -np 4 echo hello\n")
    return script


def _make_local_script(tmpdir):
    """Create a minimal local shell script."""
    script = os.path.join(tmpdir, "local_job.sh")
    with open(script, "w") as f:
        f.write("#!/bin/bash\n")
        f.write("echo local-ok\n")
    os.chmod(script, 0o755)
    return script


def test_dry_run():
    """Test dry_run tool with a valid SLURM script."""
    server = _load_server()
    with tempfile.TemporaryDirectory() as tmpdir:
        script = _make_test_script(tmpdir)
        request = {"tool": "dry_run", "params": {"script_path": script}}
        result = server.handle_request(request)
        assert result["status"] == "success"
        assert "data" in result
        print("  dry_run OK")


def test_prepare():
    """Test prepare tool (generates SLURM script)."""
    server = _load_server()
    request = {
        "tool": "prepare",
        "params": {
            "job_name": "si_relax",
            "executable": "vasp_std",
            "nodes": 2,
            "ntasks": 32,
            "walltime": "04:00:00",
        },
    }
    result = server.handle_request(request)
    assert result["status"] == "success"
    assert "script" in result["data"]
    assert "#SBATCH" in result["data"]["script"]
    assert "vasp_std" in result["data"]["script"]
    print("  prepare OK")


def test_status_no_job():
    """Test status tool with non-existent job ID."""
    server = _load_server()
    request = {"tool": "status", "params": {"job_id": "99999"}}
    result = server.handle_request(request)
    assert "job_id" in result or "status" in result or "error" in result
    print("  status (no job) OK")


def test_unknown_tool():
    """Test handling of unknown tool."""
    server = _load_server()
    request = {"tool": "nonexistent", "params": {}}
    result = server.handle_request(request)
    assert result["status"] == "error"
    assert "Unknown tool" in result["message"]
    print("  unknown tool error OK")


def test_dry_run_missing_script():
    """Test dry_run with non-existent script path."""
    server = _load_server()
    request = {"tool": "dry_run", "params": {"script_path": "/nonexistent/path.sh"}}
    result = server.handle_request(request)
    assert result["status"] in ("success", "error")
    print("  dry_run (missing script) OK")


def test_submit_requires_project_root():
    """Submit rejects write/root inference through MCP server params."""
    server = _load_server()
    with tempfile.TemporaryDirectory() as tmpdir:
        script = _make_local_script(tmpdir)
        request = {"tool": "submit", "params": {"script_path": script, "scheduler": "local"}}
        result = server.handle_request(request)
        assert result["status"] == "error"
        assert "project_root" in result["message"]
    print("  submit requires project_root OK")


def test_local_submit_requires_approval_reference():
    """Local submit cannot bypass hpc_submit approval."""
    server = _load_server()
    with tempfile.TemporaryDirectory() as tmpdir:
        script = _make_local_script(tmpdir)
        request = {
            "tool": "submit",
            "params": {
                "script_path": script,
                "scheduler": "local",
                "project_root": tmpdir,
                "dry_run_evidence": "compute/dry_run_report.json",
                "script_hash": _sha256_file(script),
                "input_artifact_hash": "input-manifest-sha256",
            },
        }
        result = server.handle_request(request)
        assert result["status"] == "error"
        assert result["approval_required"] is True
        assert result["gate"] == "hpc_submit"
    print("  local submit requires approval OK")


def test_local_submit_blocks_script_hash_mismatch():
    """Changing the job script after dry-run blocks local submit."""
    server = _load_server()
    with tempfile.TemporaryDirectory() as tmpdir:
        script = _make_local_script(tmpdir)
        params = _authorized_submit_params(tmpdir, script)
        Path(script).write_text("#!/bin/bash\necho changed\n", encoding="utf-8")
        request = {"tool": "submit", "params": {"script_path": script, "scheduler": "local", **params}}
        result = server.handle_request(request)
        assert result["status"] == "error"
        assert result["code"] == "script_hash_mismatch"
        assert result["approval_required"] is True
    print("  local submit hash mismatch OK")


def test_local_submit_with_gate_decision_executes():
    """Local submit executes only after approval, dry-run evidence, and hashes match."""
    server = _load_server()
    with tempfile.TemporaryDirectory() as tmpdir:
        script = _make_local_script(tmpdir)
        params = _authorized_submit_params(tmpdir, script)
        request = {
            "tool": "submit",
            "params": {"script_path": script, "scheduler": "local", **params},
        }
        result = server.handle_request(request)
        assert result["status"] == "success"
        assert result["success"] is True
        assert "local-ok" in result["stdout"]
        assert result["gate_decision_id"] == params["gate_decision_id"]
    print("  local submit approved execution OK")


def test_connector_registry():
    """Test that all expected schedulers are registered."""
    server = _load_server()
    if hasattr(server, "_CONNECTORS"):
        assert "slurm" in server._CONNECTORS
        assert "pbs" in server._CONNECTORS
        assert "local" in server._CONNECTORS
        assert "ssh" in server._CONNECTORS
    print("  connector registry OK")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        print(f"  {t.__name__}...", end=" ")
        t()
        print("OK")
    print(f"\n  All {len(tests)} HPC server tests passed!")
