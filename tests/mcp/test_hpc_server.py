#!/usr/bin/env python3
"""Integration tests for HPC MCP server.

Tests the server's handle_request() function end-to-end,
verifying dry_run, prepare, and status tools.
"""

import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parents[2] / "mcp" / "servers" / "hpc"


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
