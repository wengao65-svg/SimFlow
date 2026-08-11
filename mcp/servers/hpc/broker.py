"""Client for the isolated SimFlow SSH credential broker."""

from __future__ import annotations

import json
import os
import socket
import stat
import struct
from pathlib import Path

try:  # Supports both MCP script loading and package-based test imports.
    from connectors.base import BaseHPCConnector
    from transfer import normalize_target
except ModuleNotFoundError:  # pragma: no cover - exercised by package imports
    from .connectors.base import BaseHPCConnector
    from .transfer import normalize_target


MAX_MESSAGE_BYTES = 1024 * 1024


class SSHBrokerClient(BaseHPCConnector):
    """SSH connector facade that delegates credential use to a Unix broker."""

    is_ssh = True

    def __init__(self, host: str, user: str | None = None, port: int | None = None):
        target = {"host": host}
        if user is not None:
            target["user"] = user
        if port is not None:
            target["port"] = port
        self._target = normalize_target(target)

    @property
    def target(self) -> dict:
        return dict(self._target)

    @staticmethod
    def _socket_path() -> Path | None:
        value = os.environ.get("SIMFLOW_HPC_BROKER_SOCKET")
        return Path(value).expanduser() if value else None

    @staticmethod
    def _error(message: str, code: str = "hpc_broker_unavailable") -> dict:
        return {"status": "error", "message": message, "code": code}

    def _request(self, operation: str, params: dict) -> dict:
        path = self._socket_path()
        if path is None:
            return self._error("SIMFLOW_HPC_BROKER_SOCKET is not configured")
        try:
            info = path.stat()
        except OSError:
            return self._error("HPC credential broker socket is unavailable")
        if not stat.S_ISSOCK(info.st_mode):
            return self._error("HPC credential broker path is not a Unix socket", "hpc_broker_invalid_socket")
        try:
            expected_uid = int(os.environ.get("SIMFLOW_HPC_BROKER_UID", str(os.geteuid())))
            timeout = float(os.environ.get("SIMFLOW_HPC_BROKER_TIMEOUT", "30"))
        except ValueError:
            return self._error("HPC broker UID or timeout configuration is invalid", "hpc_broker_invalid_config")
        if info.st_uid != expected_uid or info.st_mode & 0o077:
            return self._error("HPC credential broker socket ownership or permissions are unsafe", "hpc_broker_unsafe_socket")

        payload = json.dumps(
            {"version": 1, "operation": operation, "target": self.target, "params": params},
            separators=(",", ":"),
        ).encode("utf-8") + b"\n"
        if len(payload) > MAX_MESSAGE_BYTES:
            return self._error("HPC broker request is too large", "hpc_broker_request_too_large")

        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.settimeout(timeout)
                client.connect(str(path))
                if not hasattr(socket, "SO_PEERCRED"):
                    return self._error("SO_PEERCRED is unavailable on this platform", "hpc_broker_peer_unverified")
                credentials = client.getsockopt(
                    socket.SOL_SOCKET,
                    socket.SO_PEERCRED,
                    struct.calcsize("3i"),
                )
                _pid, broker_uid, _gid = struct.unpack("3i", credentials)
                if broker_uid != expected_uid:
                    return self._error("HPC credential broker uid is not trusted", "hpc_broker_untrusted_peer")
                client.sendall(payload)
                chunks = bytearray()
                while b"\n" not in chunks:
                    chunk = client.recv(65536)
                    if not chunk:
                        break
                    chunks.extend(chunk)
                    if len(chunks) > MAX_MESSAGE_BYTES:
                        return self._error("HPC broker response is too large", "hpc_broker_response_too_large")
        except (OSError, ValueError) as exc:
            return self._error(f"HPC credential broker request failed: {type(exc).__name__}")

        try:
            response = json.loads(bytes(chunks).split(b"\n", 1)[0].decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return self._error("HPC credential broker returned an invalid response", "hpc_broker_invalid_response")
        if not isinstance(response, dict):
            return self._error("HPC credential broker returned a non-object response", "hpc_broker_invalid_response")
        return response

    def dry_run(self, script_path: str, manifest_path: str = "", base_dir: str = ".") -> dict:
        issues = []
        script = Path(script_path)
        if not script.exists():
            issues.append(f"Script not found locally: {script_path}")
        response = {
            "valid": not issues,
            "issues": issues,
            "scheduler": "ssh",
            "target": self.target,
            "script": script_path,
            "execution_boundary": "broker_required_for_real_operations",
        }
        if script.exists():
            response["script_hash"] = self._sha256_file(script)
        return response

    def submit(self, script_path: str, **kwargs) -> dict:
        auth = self.validate_submit_authorization(
            script_path,
            project_root=kwargs.get("project_root"),
            approval_token=kwargs.get("approval_token"),
            gate_decision_id=kwargs.get("gate_decision_id"),
            run_plan_hash=kwargs.get("run_plan_hash"),
            expected_scheduler="ssh",
            approval_bindings={
                "target": kwargs.get("target"),
                "remote_workdir": kwargs.get("remote_workdir"),
            },
            approved=kwargs.get("approved"),
        )
        if auth["status"] != "success":
            return auth
        return self._request("submit", {"script_path": script_path, "kwargs": kwargs})

    def status(self, job_id: str) -> dict:
        return self._request("status", {"job_id": str(job_id)})

    def cancel(self, job_id: str) -> dict:
        return self._request("cancel", {"job_id": str(job_id)})

    def upload_files(self, local_dir: str, remote_dir: str, files: list[str]) -> dict:
        return self._request(
            "upload_files",
            {"local_dir": local_dir, "remote_dir": remote_dir, "files": files},
        )

    def download_files(self, remote_dir: str, local_dir: str, files: list[str]) -> dict:
        return self._request(
            "download_files",
            {"remote_dir": remote_dir, "local_dir": local_dir, "files": files},
        )

    def list_remote_files(self, remote_dir: str, paths: list[str]) -> dict:
        return self._request("list_remote_files", {"remote_dir": remote_dir, "paths": paths})

    def remote_file_manifest(self, remote_dir: str, files: list[str]) -> dict:
        return self._request("remote_file_manifest", {"remote_dir": remote_dir, "files": files})
