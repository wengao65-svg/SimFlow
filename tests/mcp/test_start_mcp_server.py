#!/usr/bin/env python3
"""Tests for Codex-style SimFlow MCP startup wrapper."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STARTER = ROOT / "scripts" / "start_mcp_server.py"
SERVERS = [
    "simflow_state",
    "artifact_store",
    "checkpoint_store",
    "literature",
    "structure",
    "hpc",
    "parsers",
]


def _mcp_payload() -> str:
    return "\n".join([
        json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05"},
        }),
        json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}),
        json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}),
        json.dumps({"jsonrpc": "2.0", "id": 3, "method": "shutdown", "params": {}}),
        "",
    ])


def _run_from_non_plugin_cwd(server_name: str) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as tmpdir:
        return subprocess.run(
            [sys.executable, str(STARTER), server_name],
            cwd=tmpdir,
            input=_mcp_payload(),
            text=True,
            capture_output=True,
            timeout=5,
        )


def test_all_mcp_servers_initialize_from_non_plugin_cwd():
    for server_name in SERVERS:
        result = _run_from_non_plugin_cwd(server_name)
        assert result.returncode == 0, result.stderr
        assert result.stderr == ""
        lines = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
        assert lines[0]["result"]["serverInfo"]["name"] == server_name
        assert len(lines[1]["result"]["tools"]) > 0


def test_invalid_mcp_server_name_writes_only_stderr():
    with tempfile.TemporaryDirectory() as tmpdir:
        result = subprocess.run(
            [sys.executable, str(STARTER), "not_a_server"],
            cwd=tmpdir,
            text=True,
            capture_output=True,
            timeout=5,
        )
    assert result.returncode != 0
    assert result.stdout == ""
    assert "Unknown SimFlow MCP server" in result.stderr
