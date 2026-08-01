"""Safe local-path and transfer-manifest helpers for the HPC MCP server."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
from typing import Iterable


class TransferValidationError(ValueError):
    """Raised when a transfer request crosses a path or input boundary."""


def _safe_relative(value: str, field: str = "path") -> str:
    if not isinstance(value, str) or not value.strip():
        raise TransferValidationError(f"{field} must be a non-empty relative path")
    if "\x00" in value or "\n" in value or "\r" in value or "\t" in value:
        raise TransferValidationError(f"{field} contains forbidden control characters")
    path = PurePosixPath(value.replace(os.sep, "/"))
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise TransferValidationError(f"{field} must not be absolute or contain . / .. components")
    return path.as_posix()


def resolve_project_path(project_root: str | Path, value: str | Path, field: str) -> Path:
    root = Path(project_root).expanduser().resolve()
    candidate = Path(value).expanduser()
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise TransferValidationError(f"{field} must remain inside project_root") from exc
    return resolved


def validate_remote_dir(remote_dir: str) -> str:
    if not isinstance(remote_dir, str) or not remote_dir.startswith("/"):
        raise TransferValidationError("remote_dir must be an absolute POSIX path")
    if "\x00" in remote_dir or "\n" in remote_dir or "\r" in remote_dir:
        raise TransferValidationError("remote_dir contains forbidden control characters")
    path = PurePosixPath(remote_dir)
    if ".." in path.parts:
        raise TransferValidationError("remote_dir must not contain .. components")
    return path.as_posix()


def expand_local_paths(local_dir: str | Path, paths: Iterable[str]) -> list[tuple[str, Path]]:
    root = Path(local_dir).resolve()
    expanded: dict[str, Path] = {}
    for raw in paths:
        rel = _safe_relative(raw)
        candidate = (root / rel).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise TransferValidationError("path escapes local_dir") from exc
        if candidate.is_symlink():
            raise TransferValidationError(f"symlink transfers are not allowed: {rel}")
        if candidate.is_file():
            expanded[rel] = candidate
        elif candidate.is_dir():
            for child in sorted(candidate.rglob("*")):
                if child.is_symlink():
                    raise TransferValidationError(f"symlink transfers are not allowed: {child}")
                if child.is_file():
                    child_rel = child.relative_to(root).as_posix()
                    expanded[child_rel] = child
        else:
            raise TransferValidationError(f"transfer path does not exist: {rel}")
    return sorted(expanded.items())


def file_manifest(files: Iterable[tuple[str, Path]]) -> dict:
    entries = []
    total_size = 0
    for rel, path in files:
        digest = hashlib.sha256()
        size = 0
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
                size += len(chunk)
        entries.append({"path": rel, "size_bytes": size, "sha256": digest.hexdigest()})
        total_size += size
    entries.sort(key=lambda item: item["path"])
    canonical = json.dumps(entries, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return {
        "algorithm": "sha256-path-size-content-v1",
        "file_count": len(entries),
        "total_size_bytes": total_size,
        "files": entries,
        "manifest_sha256": hashlib.sha256(canonical).hexdigest(),
    }


def remote_manifest(files: Iterable[dict]) -> dict:
    entries = sorted(
        [{"path": item["path"], "size_bytes": int(item["size_bytes"]), "sha256": item["sha256"]} for item in files],
        key=lambda item: item["path"],
    )
    canonical = json.dumps(entries, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return {
        "algorithm": "sha256-path-size-content-v1",
        "file_count": len(entries),
        "total_size_bytes": sum(item["size_bytes"] for item in entries),
        "files": entries,
        "manifest_sha256": hashlib.sha256(canonical).hexdigest(),
    }


def manifests_match(expected: dict, actual: dict) -> bool:
    return expected.get("files", []) == actual.get("files", [])


def request_fingerprint(direction: str, remote_dir: str, paths: Iterable[str]) -> str:
    payload = {
        "direction": direction,
        "remote_dir": validate_remote_dir(remote_dir),
        "paths": sorted(_safe_relative(path) for path in paths),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
