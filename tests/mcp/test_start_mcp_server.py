#!/usr/bin/env python3
"""Tests for Codex-style SimFlow MCP startup wrapper."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STARTER = ROOT / "scripts" / "start_mcp_server.py"
SERVERS = [
    "simflow_state",
    "hpc",
]
COMPATIBILITY_SERVERS = ["artifact_store", "checkpoint_store"]


def _mcp_payload(client_name: str | None = None) -> str:
    initialize_params = {"protocolVersion": "2024-11-05"}
    if client_name:
        initialize_params["clientInfo"] = {"name": client_name, "version": "test"}
    return "\n".join([
        json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": initialize_params,
        }),
        json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}),
        json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}),
        json.dumps({"jsonrpc": "2.0", "id": 3, "method": "shutdown", "params": {}}),
        "",
    ])


def _run_from_non_plugin_cwd(
    server_name: str,
    env: dict[str, str] | None = None,
    client_name: str | None = None,
) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as tmpdir:
        return subprocess.run(
            [sys.executable, str(STARTER), server_name],
            cwd=tmpdir,
            env=env,
            input=_mcp_payload(client_name),
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
        tools = lines[1]["result"]["tools"]
        assert len(tools) > 0
        for tool in tools:
            schema = tool["inputSchema"]
            assert schema["type"] == "object"
            assert schema["additionalProperties"] is False
            assert "properties" in schema


def test_v012_compatibility_servers_still_initialize_but_are_not_public():
    for server_name in COMPATIBILITY_SERVERS:
        result = _run_from_non_plugin_cwd(server_name)
        assert result.returncode == 0, result.stderr
        lines = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
        assert lines[0]["result"]["serverInfo"]["name"] == server_name
        assert lines[1]["result"]["tools"]


def test_stdio_schema_fallback_is_strict():
    from mcp.shared.stdio_server import _list_tools

    listed = _list_tools({"noop": lambda params: {"status": "success"}})
    assert listed[0]["inputSchema"] == {
        "type": "object",
        "additionalProperties": False,
        "properties": {},
    }


def test_state_server_initialization_adapts_to_mcp_client_info():
    codex = _run_from_non_plugin_cwd("simflow_state", client_name="codex-cli")
    claude = _run_from_non_plugin_cwd("simflow_state", client_name="claude-code")
    opencode = _run_from_non_plugin_cwd("simflow_state", client_name="opencode")
    generic = _run_from_non_plugin_cwd("simflow_state", client_name="other")

    codex_result = json.loads(codex.stdout.splitlines()[0])["result"]
    claude_result = json.loads(claude.stdout.splitlines()[0])["result"]
    opencode_result = json.loads(opencode.stdout.splitlines()[0])["result"]
    generic_result = json.loads(generic.stdout.splitlines()[0])["result"]
    assert "$simflow" in codex_result["instructions"]
    assert "/simflow:simflow" in claude_result["instructions"]
    assert "skill tool" in opencode_result["instructions"]
    assert "$simflow" not in generic_result["instructions"]


def test_non_state_server_does_not_duplicate_host_instructions():
    result = _run_from_non_plugin_cwd("artifact_store", client_name="codex-cli")
    initialize = json.loads(result.stdout.splitlines()[0])["result"]
    assert "instructions" not in initialize


def test_stdio_tools_call_cannot_bypass_repair_apply_engagement():
    from runtime.simflow_core.state import init_workflow

    with tempfile.TemporaryDirectory() as project_root, tempfile.TemporaryDirectory() as cwd:
        init_workflow("custom", "computation", project_root=project_root)
        payload = "\n".join([
            json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "clientInfo": {"name": "codex-cli", "version": "test"},
                },
            }),
            json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}),
            json.dumps({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "repair_state",
                    "arguments": {"project_root": project_root, "mode": "apply"},
                },
            }),
            json.dumps({"jsonrpc": "2.0", "id": 3, "method": "shutdown", "params": {}}),
            "",
        ])
        result = subprocess.run(
            [sys.executable, str(STARTER), "simflow_state"],
            cwd=cwd,
            input=payload,
            text=True,
            capture_output=True,
            timeout=5,
        )

    responses = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    tool_text = responses[1]["result"]["content"][0]["text"]
    tool_result = json.loads(tool_text)
    assert tool_result["code"] == "skill_engagement_contract_violation"


def test_mcp_startup_prefers_repo_package_when_third_party_mcp_exists():
    with tempfile.TemporaryDirectory() as tmpdir:
        fake_mcp = Path(tmpdir) / "mcp"
        fake_mcp.mkdir()
        (fake_mcp / "__init__.py").write_text(
            "raise RuntimeError('third-party mcp package was imported')\n",
            encoding="utf-8",
        )
        env = os.environ.copy()
        existing_pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = tmpdir if not existing_pythonpath else f"{tmpdir}{os.pathsep}{existing_pythonpath}"

        result = _run_from_non_plugin_cwd("simflow_state", env=env)

    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    lines = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    assert lines[0]["result"]["serverInfo"]["name"] == "simflow_state"
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
