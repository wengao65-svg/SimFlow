"""Explicit, non-destructive migration from legacy SimFlow state."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .records import list_project_records, record_event
from .state import resolve_project_root


MIGRATION_REPORT_SCHEMA = "simflow.migration_report.v1"
MIGRATION_INDEX_SCHEMA = "simflow.migration_index.v1"
MAX_NESTED_ROOTS = 200
MAX_MEMORY_FILES = 2000
SQLITE_HEADER = b"SQLite format 3\x00"


class MigrationError(ValueError):
    """Raised when migration confirmation or source state is invalid."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _json_shape(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {"valid_json": False, "json_type": None, "entry_count": None, "error": type(exc).__name__}
    if isinstance(payload, dict):
        count = len(payload)
        json_type = "object"
    elif isinstance(payload, list):
        count = len(payload)
        json_type = "array"
    else:
        count = 1
        json_type = type(payload).__name__
    return {
        "valid_json": True,
        "json_type": json_type,
        "entry_count": count,
    }


def _jsonl_shape(path: Path) -> dict[str, Any]:
    entry_count = 0
    json_types: set[str] = set()
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                payload = json.loads(line)
                entry_count += 1
                if isinstance(payload, dict):
                    json_types.add("object")
                elif isinstance(payload, list):
                    json_types.add("array")
                else:
                    json_types.add(type(payload).__name__)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {
            "valid_jsonl": False,
            "json_types": [],
            "entry_count": None,
            "error": type(exc).__name__,
        }
    return {
        "valid_jsonl": True,
        "json_types": sorted(json_types),
        "entry_count": entry_count,
    }


def _sqlite_header_metadata(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("rb") as handle:
            header = handle.read(100)
    except OSError:
        return None
    if len(header) < 100 or not header.startswith(SQLITE_HEADER):
        return None
    page_size = int.from_bytes(header[16:18], "big")
    if page_size == 1:
        page_size = 65536
    return {
        "format": "sqlite3",
        "page_size": page_size,
        "write_version": header[18],
        "read_version": header[19],
        "database_size_pages": int.from_bytes(header[28:32], "big"),
        "schema_cookie": int.from_bytes(header[40:44], "big"),
        "schema_format": int.from_bytes(header[44:48], "big"),
        "user_version": int.from_bytes(header[60:64], "big"),
        "application_id": int.from_bytes(header[68:72], "big"),
        "sqlite_version_number": int.from_bytes(header[96:100], "big"),
        "tables_inspected": False,
    }


def _memory_file_metadata(root: Path, path: Path) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "path": _relative(root, path),
        "size_bytes": path.stat().st_size,
        "sha256": _sha256(path),
    }
    sqlite_metadata = _sqlite_header_metadata(path)
    if sqlite_metadata is not None:
        metadata["sqlite"] = sqlite_metadata
    elif path.suffix.lower() == ".json":
        metadata["json_shape"] = _json_shape(path)
    elif path.suffix.lower() == ".jsonl":
        metadata["jsonl_shape"] = _jsonl_shape(path)
    return metadata


def _memory_inventory(root: Path, memory_dir: Path) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    truncated = False
    if memory_dir.is_dir():
        for current, directories, names in os.walk(memory_dir, followlinks=False):
            directories[:] = sorted(
                name for name in directories
                if not (Path(current) / name).is_symlink()
            )
            for name in sorted(names):
                path = Path(current) / name
                try:
                    mode = path.lstat().st_mode
                except OSError:
                    continue
                if not stat.S_ISREG(mode):
                    continue
                files.append(_memory_file_metadata(root, path))
                if len(files) >= MAX_MEMORY_FILES:
                    truncated = True
                    break
            if truncated:
                break
    return {
        "memory_dir": _relative(root, memory_dir),
        "memory_files": files,
        "memory_file_count": len(files),
        "memory_scan_truncated": truncated,
        "content_imported": False,
        "sqlite_tables_inspected": False,
    }


def _state_inventory(root: Path, state_dir: Path) -> dict[str, Any]:
    files = []
    if state_dir.is_dir():
        for path in sorted(state_dir.glob("*.json")):
            if not path.is_file():
                continue
            files.append({
                "path": _relative(root, path),
                "size_bytes": path.stat().st_size,
                "sha256": _sha256(path),
                **_json_shape(path),
            })
    return {
        "state_dir": _relative(root, state_dir),
        "state_files": files,
        "state_file_count": len(files),
    }


def _nested_simflow_roots(root: Path) -> tuple[list[dict[str, Any]], bool]:
    nested: list[dict[str, Any]] = []
    truncated = False
    for current, directories, _files in os.walk(root):
        current_path = Path(current)
        directories[:] = [name for name in directories if name not in {".git", "__pycache__"}]
        if current_path == root and ".simflow" in directories:
            directories.remove(".simflow")
        if ".simflow" not in directories:
            continue
        nested_root = current_path / ".simflow"
        directories.remove(".simflow")
        nested.append({
            "path": _relative(root, nested_root),
            **_state_inventory(root, nested_root / "state"),
            **_memory_inventory(root, nested_root / "memory"),
        })
        if len(nested) >= MAX_NESTED_ROOTS:
            truncated = True
            break
    return nested, truncated


def build_migration_report(project_root: str) -> dict[str, Any]:
    """Inspect legacy state and propose a compact index without writing."""
    root = resolve_project_root(project_root=project_root)
    legacy = _state_inventory(root, root / ".simflow" / "state")
    legacy_memory = _memory_inventory(root, root / ".simflow" / "memory")
    nested, truncated = _nested_simflow_roots(root)
    detected = bool(legacy["state_files"] or legacy_memory["memory_files"] or nested)
    proposed_index = {
        "schema_version": MIGRATION_INDEX_SCHEMA,
        "legacy_state": legacy,
        "legacy_memory": legacy_memory,
        "nested_simflow_roots": nested,
        "nested_scan_truncated": truncated,
        "source_scope": "structured_simflow_state_and_memory_metadata",
        "host_transcripts_imported": False,
        "scientific_data_actions": [],
        "automatic_moves": [],
        "automatic_renames": [],
        "automatic_deletes": [],
        "automatic_rewrites": [],
    }
    report_hash = hashlib.sha256(_canonical_json(proposed_index).encode("utf-8")).hexdigest()
    return {
        "schema_version": MIGRATION_REPORT_SCHEMA,
        "detected": detected,
        "requires_confirmation": detected,
        "migration_report_hash": report_hash,
        "proposed_index": proposed_index,
        "proposed_record_count": 1 if detected else 0,
        "confirmation_contract": {
            "tool": "simflow_state/record",
            "kind": "migration",
            "confirm_migration": True,
            "migration_report_hash": report_hash,
        },
        "safety": {
            "source_files_are_read_only": True,
            "legacy_memory_content_is_not_imported": True,
            "sqlite_tables_are_not_inspected": True,
            "scientific_data_is_not_moved": True,
            "nested_simflow_is_not_modified": True,
            "host_transcripts_are_not_imported": True,
        },
    }


def _existing_migration(project_root: str, report_hash: str) -> dict[str, Any] | None:
    for record in list_project_records(project_root, kind="migration"):
        details = record.get("details") if isinstance(record.get("details"), dict) else {}
        if details.get("migration_report_hash") == report_hash:
            return record
    return None


def apply_migration(
    project_root: str,
    *,
    migration_report_hash: str,
    confirm_migration: bool,
    summary: str = "Index legacy SimFlow state",
) -> dict[str, Any]:
    """Append one compact migration index after explicit hash confirmation."""
    if confirm_migration is not True:
        raise MigrationError("confirm_migration=true is required")
    report = build_migration_report(project_root)
    if not report["detected"]:
        raise MigrationError("No legacy state or nested .simflow directories were detected")
    if migration_report_hash != report["migration_report_hash"]:
        raise MigrationError("migration_report_hash is stale or does not match the current source inventory")
    existing = _existing_migration(project_root, migration_report_hash)
    if existing is not None:
        return {"status": "already_applied", "record": existing, "report": report}

    root = resolve_project_root(project_root=project_root)
    report_path = root / ".simflow" / "reports" / "migration" / f"{migration_report_hash}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    persisted_report = {**report, "confirmed_at": _now_iso()}
    report_path.write_text(
        json.dumps(persisted_report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    record = record_event(
        str(root),
        kind="migration",
        summary=summary,
        status="completed",
        artifacts=[{"path": str(report_path.relative_to(root)), "role": "migration_report"}],
        details={
            "migration_report_hash": migration_report_hash,
            "source_scope": "structured_simflow_state_and_memory_metadata",
            "legacy_state_file_count": report["proposed_index"]["legacy_state"]["state_file_count"],
            "legacy_memory_file_count": report["proposed_index"]["legacy_memory"]["memory_file_count"],
            "nested_simflow_count": len(report["proposed_index"]["nested_simflow_roots"]),
            "host_transcripts_imported": False,
            "scientific_data_actions": [],
            "proposed_index": report["proposed_index"],
        },
    )
    return {"status": "applied", "record": record, "report": report}
