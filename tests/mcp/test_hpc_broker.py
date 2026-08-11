"""Tests for the isolated Unix-socket HPC credential broker."""

from __future__ import annotations

import os
import socket
import stat
import threading
from pathlib import Path

import pytest

from mcp.servers.hpc.broker import SSHBrokerClient
from mcp.servers.hpc.broker_server import SSHBrokerServer


def _serve_once(server: SSHBrokerServer) -> threading.Thread:
    thread = threading.Thread(target=server.serve_once, daemon=True)
    thread.start()
    return thread


def test_broker_client_fails_closed_without_socket(monkeypatch):
    monkeypatch.delenv("SIMFLOW_HPC_BROKER_SOCKET", raising=False)
    result = SSHBrokerClient(host="hpc").status("123")
    assert result["status"] == "error"
    assert result["code"] == "hpc_broker_unavailable"


def test_broker_client_rejects_non_socket_path(tmp_path, monkeypatch):
    path = tmp_path / "broker.sock"
    path.write_text("not a socket", encoding="utf-8")
    monkeypatch.setenv("SIMFLOW_HPC_BROKER_SOCKET", str(path))

    result = SSHBrokerClient(host="hpc").status("123")
    assert result["code"] == "hpc_broker_invalid_socket"


def test_broker_socket_is_owner_only(tmp_path):
    server = SSHBrokerServer(tmp_path / "broker.sock")
    try:
        server.start()
        mode = stat.S_IMODE(server.socket_path.stat().st_mode)
        assert mode == 0o600
        assert server.socket_path.stat().st_uid == os.geteuid()
    finally:
        server.close()


def test_broker_round_trip_status_uses_fixed_operation(tmp_path, monkeypatch):
    from mcp.servers.hpc import broker_server

    monkeypatch.setattr(
        broker_server.SSHConnector,
        "status",
        lambda self, job_id: {"status": "success", "data": {"job_id": job_id, "target": self.target}},
    )
    server = SSHBrokerServer(tmp_path / "broker.sock")
    server.start()
    monkeypatch.setenv("SIMFLOW_HPC_BROKER_SOCKET", str(server.socket_path))
    thread = _serve_once(server)
    try:
        result = SSHBrokerClient(host="hpc").status("123")
        assert result == {"status": "success", "data": {"job_id": "123", "target": {"host": "hpc"}}}
    finally:
        thread.join(timeout=5)
        server.close()


def test_broker_rejects_arbitrary_operations(tmp_path, monkeypatch):
    server = SSHBrokerServer(tmp_path / "broker.sock")
    server.start()
    monkeypatch.setenv("SIMFLOW_HPC_BROKER_SOCKET", str(server.socket_path))
    thread = _serve_once(server)
    try:
        result = SSHBrokerClient(host="hpc")._request("remote_shell", {"command": "cat ~/.ssh/id_rsa"})
        assert result["status"] == "error"
        assert result["code"] == "hpc_broker_request_rejected"
        assert "operation is not allowed" in result["message"]
        assert ".ssh/id_rsa" not in result["message"]
    finally:
        thread.join(timeout=5)
        server.close()


def test_broker_rejects_local_paths_outside_allowed_roots(tmp_path, monkeypatch):
    allowed = tmp_path / "project"
    outside = tmp_path / "outside"
    allowed.mkdir()
    outside.mkdir()
    monkeypatch.setenv("SIMFLOW_HPC_BROKER_ALLOWED_ROOTS", str(allowed))
    server = SSHBrokerServer(tmp_path / "broker.sock")
    server.start()
    monkeypatch.setenv("SIMFLOW_HPC_BROKER_SOCKET", str(server.socket_path))
    thread = _serve_once(server)
    try:
        result = SSHBrokerClient(host="hpc").upload_files(str(outside), "/scratch/job", ["input.txt"])
        assert result["status"] == "error"
        assert "outside broker allowed roots" in result["message"]
    finally:
        thread.join(timeout=5)
        server.close()


def test_broker_rejects_remote_path_traversal(tmp_path, monkeypatch):
    allowed = tmp_path / "project"
    allowed.mkdir()
    monkeypatch.setenv("SIMFLOW_HPC_BROKER_ALLOWED_ROOTS", str(allowed))
    server = SSHBrokerServer(tmp_path / "broker.sock")
    server.start()
    monkeypatch.setenv("SIMFLOW_HPC_BROKER_SOCKET", str(server.socket_path))
    thread = _serve_once(server)
    try:
        result = SSHBrokerClient(host="hpc").upload_files(str(allowed), "/scratch/job", ["../secret"])
        assert result["status"] == "error"
        assert "must not be absolute or contain" in result["message"]
    finally:
        thread.join(timeout=5)
        server.close()


def test_broker_rejects_unapproved_peer_uid(tmp_path, monkeypatch):
    from mcp.servers.hpc import broker_server

    dispatched = []
    monkeypatch.setattr(broker_server, "_dispatch", lambda request: dispatched.append(request))
    monkeypatch.setenv("SIMFLOW_HPC_BROKER_ALLOWED_UID", str(os.geteuid() + 1))
    server = SSHBrokerServer(tmp_path / "broker.sock")
    server.start()
    monkeypatch.setenv("SIMFLOW_HPC_BROKER_SOCKET", str(server.socket_path))
    thread = _serve_once(server)
    try:
        result = SSHBrokerClient(host="hpc").status("123")
        assert result["status"] == "error"
        assert "peer uid" in result["message"]
        assert dispatched == []
    finally:
        thread.join(timeout=5)
        server.close()
