#!/usr/bin/env python3
"""Tests for Codex-style SimFlow MCP startup wrapper."""

import json
import os
import subprocess
import sys
import tempfile
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
STARTER = ROOT / "scripts" / "start_mcp_server.py"
SERVERS = [
    "simflow_state",
    "hpc",
]


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
    result = _run_from_non_plugin_cwd("hpc", client_name="codex-cli")
    initialize = json.loads(result.stdout.splitlines()[0])["result"]
    assert "instructions" not in initialize


def test_removed_storage_server_names_are_rejected():
    for server_name in ("artifact_store", "checkpoint_store"):
        result = _run_from_non_plugin_cwd(server_name)
        assert result.returncode != 0
        assert result.stdout == ""
        assert "Unknown SimFlow MCP server" in result.stderr


def test_hpc_startup_does_not_inherit_ssh_agent_socket(monkeypatch):
    spec = importlib.util.spec_from_file_location("simflow_mcp_starter", STARTER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    captured = {}

    def fake_execvpe(executable, argv, env):
        captured["env"] = env
        raise RuntimeError("captured")

    monkeypatch.setenv("SSH_AUTH_SOCK", "/tmp/agent.sock")
    monkeypatch.setenv("SSH_AGENT_PID", "123")
    monkeypatch.setattr(module.os, "execvpe", fake_execvpe)
    previous_cwd = Path.cwd()
    try:
        with pytest.raises(RuntimeError, match="captured"):
            module.main([str(STARTER), "hpc"])
    finally:
        os.chdir(previous_cwd)

    assert "SSH_AUTH_SOCK" not in captured["env"]
    assert "SSH_AGENT_PID" not in captured["env"]


def test_stdio_record_does_not_require_engagement_bootstrap():
    with tempfile.TemporaryDirectory() as project_root, tempfile.TemporaryDirectory() as cwd:
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
                    "name": "record",
                    "arguments": {
                        "project_root": project_root,
                        "kind": "note",
                        "summary": "stdio direct record",
                    },
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
        assert tool_result["status"] == "success"
        assert (Path(project_root) / ".simflow" / "records.jsonl").is_file()


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
