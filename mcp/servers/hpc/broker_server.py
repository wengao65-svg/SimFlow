"""Isolated Unix-socket broker for bounded SSH credential operations."""

from __future__ import annotations

import argparse
import json
import os
import socket
import stat
import struct
from pathlib import Path

try:  # Supports both direct script and package imports.
    from connectors.ssh import SSHConnector
    from transfer import _safe_relative, normalize_target, validate_remote_dir
except ModuleNotFoundError:  # pragma: no cover
    from .connectors.ssh import SSHConnector
    from .transfer import _safe_relative, normalize_target, validate_remote_dir


MAX_MESSAGE_BYTES = 1024 * 1024
OPERATIONS = {
    "submit",
    "status",
    "cancel",
    "upload_files",
    "download_files",
    "list_remote_files",
    "remote_file_manifest",
}


class BrokerRequestError(ValueError):
    """Raised when a broker request violates the protocol boundary."""


def _allowed_roots() -> list[Path]:
    raw = os.environ.get("SIMFLOW_HPC_BROKER_ALLOWED_ROOTS", "")
    return [Path(value).expanduser().resolve() for value in raw.split(os.pathsep) if value]


def _require_allowed_path(value: str, field: str) -> Path:
    if not isinstance(value, str) or not value:
        raise BrokerRequestError(f"{field} is required")
    path = Path(value).expanduser().resolve()
    roots = _allowed_roots()
    if not roots:
        raise BrokerRequestError("SIMFLOW_HPC_BROKER_ALLOWED_ROOTS is not configured")
    if not any(path == root or path.is_relative_to(root) for root in roots):
        raise BrokerRequestError(f"{field} is outside broker allowed roots")
    return path


def _safe_remote_paths(values: object, field: str) -> list[str]:
    if not isinstance(values, list) or not values:
        raise BrokerRequestError(f"{field} must be a non-empty list")
    try:
        return [_safe_relative(value, field) for value in values]
    except ValueError as exc:
        raise BrokerRequestError(str(exc)) from exc


def _peer_uid(connection: socket.socket) -> int:
    if not hasattr(socket, "SO_PEERCRED"):
        raise BrokerRequestError("SO_PEERCRED is unavailable on this platform")
    credentials = connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
    _pid, uid, _gid = struct.unpack("3i", credentials)
    return uid


def _receive_request(connection: socket.socket) -> dict:
    chunks = bytearray()
    while b"\n" not in chunks:
        chunk = connection.recv(65536)
        if not chunk:
            break
        chunks.extend(chunk)
        if len(chunks) > MAX_MESSAGE_BYTES:
            raise BrokerRequestError("request exceeds broker size limit")
    try:
        request = json.loads(bytes(chunks).split(b"\n", 1)[0].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BrokerRequestError("request is not valid JSON") from exc
    if not isinstance(request, dict) or request.get("version") != 1:
        raise BrokerRequestError("unsupported broker protocol version")
    return request


def _dispatch(request: dict) -> dict:
    operation = request.get("operation")
    if operation not in OPERATIONS:
        raise BrokerRequestError("operation is not allowed")
    target = normalize_target(request.get("target"))
    params = request.get("params")
    if not isinstance(params, dict):
        raise BrokerRequestError("params must be an object")
    connector = SSHConnector(**target)

    if operation == "status":
        return connector.status(params.get("job_id", ""))
    if operation == "cancel":
        return connector.cancel(params.get("job_id", ""))
    if operation == "list_remote_files":
        remote_dir = validate_remote_dir(params.get("remote_dir", ""))
        return connector.list_remote_files(remote_dir, _safe_remote_paths(params.get("paths"), "paths"))
    if operation == "remote_file_manifest":
        remote_dir = validate_remote_dir(params.get("remote_dir", ""))
        return connector.remote_file_manifest(remote_dir, _safe_remote_paths(params.get("files"), "files"))
    if operation == "upload_files":
        local_dir = _require_allowed_path(params.get("local_dir", ""), "local_dir")
        remote_dir = validate_remote_dir(params.get("remote_dir", ""))
        return connector.upload_files(str(local_dir), remote_dir, _safe_remote_paths(params.get("files"), "files"))
    if operation == "download_files":
        local_dir = _require_allowed_path(params.get("local_dir", ""), "local_dir")
        remote_dir = validate_remote_dir(params.get("remote_dir", ""))
        return connector.download_files(remote_dir, str(local_dir), _safe_remote_paths(params.get("files"), "files"))

    script_path = _require_allowed_path(params.get("script_path", ""), "script_path")
    kwargs = params.get("kwargs")
    if not isinstance(kwargs, dict):
        raise BrokerRequestError("submit kwargs must be an object")
    project_root = _require_allowed_path(kwargs.get("project_root", ""), "project_root")
    if not script_path.is_relative_to(project_root):
        raise BrokerRequestError("script_path must remain inside project_root")
    kwargs["project_root"] = str(project_root)
    return connector.submit(str(script_path), **kwargs)


class SSHBrokerServer:
    """Single-process bounded broker suitable for a host-managed service."""

    def __init__(self, socket_path: str | Path):
        self.socket_path = Path(socket_path).expanduser()
        self.socket: socket.socket | None = None
        self._socket_identity: tuple[int, int] | None = None

    def start(self) -> None:
        self.socket_path.parent.mkdir(parents=True, exist_ok=True)
        if self.socket_path.exists() or self.socket_path.is_symlink():
            info = self.socket_path.lstat()
            kind = "socket" if stat.S_ISSOCK(info.st_mode) else "non-socket path"
            raise BrokerRequestError(f"broker {kind} already exists; refusing to replace it")
        previous_umask = os.umask(0o077)
        server = None
        try:
            server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server.bind(str(self.socket_path))
            os.chmod(self.socket_path, 0o600)
            server.listen(16)
            self.socket = server
            info = self.socket_path.lstat()
            self._socket_identity = (info.st_dev, info.st_ino)
        except Exception:
            if server is not None:
                server.close()
            if self.socket_path.exists() and stat.S_ISSOCK(self.socket_path.lstat().st_mode):
                self.socket_path.unlink()
            raise
        finally:
            os.umask(previous_umask)

    def serve_once(self) -> None:
        if self.socket is None:
            self.start()
        assert self.socket is not None
        connection, _ = self.socket.accept()
        with connection:
            try:
                allowed_uid = int(os.environ.get("SIMFLOW_HPC_BROKER_ALLOWED_UID", str(os.geteuid())))
                if _peer_uid(connection) != allowed_uid:
                    raise BrokerRequestError("broker peer uid is not allowed")
                response = _dispatch(_receive_request(connection))
            except Exception as exc:
                response = {
                    "status": "error",
                    "code": "hpc_broker_request_rejected",
                    "message": SSHConnector._safe_error(exc, "broker request rejected"),
                }
            try:
                connection.sendall(json.dumps(response, separators=(",", ":")).encode("utf-8") + b"\n")
            except OSError:
                pass

    def serve_forever(self) -> None:
        if self.socket is None:
            self.start()
        while True:
            self.serve_once()

    def close(self) -> None:
        if self.socket is not None:
            self.socket.close()
            self.socket = None
        if self.socket_path.exists():
            info = self.socket_path.lstat()
            identity = (info.st_dev, info.st_ino)
            if stat.S_ISSOCK(info.st_mode) and identity == self._socket_identity:
                self.socket_path.unlink()
        self._socket_identity = None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the isolated SimFlow HPC credential broker")
    parser.add_argument("--socket", default=os.environ.get("SIMFLOW_HPC_BROKER_SOCKET"))
    args = parser.parse_args(argv)
    if not args.socket:
        parser.error("--socket or SIMFLOW_HPC_BROKER_SOCKET is required")
    server = SSHBrokerServer(args.socket)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
