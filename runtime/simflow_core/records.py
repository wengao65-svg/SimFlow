"""Compact SimFlow project records and recovery references.

The canonical v2 store is intentionally small:

* ``.simflow/project.json`` is a derived current-project summary.
* ``.simflow/records.jsonl`` is the append-only event record.
* ``.simflow/checkpoints/`` contains compact recovery references.

Legacy ``.simflow/state/*.json`` registries remain readable through
``inspect_project`` but are never rewritten by this module.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .state import ProjectRootError, resolve_project_path, resolve_project_root


PROJECT_SCHEMA = "simflow.project.v1"
RECORD_SCHEMA = "simflow.record.v1"
CHECKPOINT_SCHEMA = "simflow.checkpoint.v1"

RECORD_KINDS = (
    "milestone",
    "run",
    "artifact",
    "analysis",
    "approval",
    "failure",
    "note",
    "checkpoint",
    "recovery",
)
ACTIVE_RUN_STATUSES = {"planned", "prepared", "submitted", "queued", "running", "paused"}
TERMINAL_RUN_STATUSES = {"completed", "failed", "cancelled", "abandoned"}
CHECKPOINT_STATUSES = ("ready", "partial", "diagnostic")

_PRIVATE_KEY_PATTERN = re.compile(
    r"-----BEGIN (?:OPENSSH|RSA|DSA|EC|ENCRYPTED) PRIVATE KEY-----",
    re.IGNORECASE,
)
_BEARER_PATTERN = re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE)
_SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(password|passwd|passphrase|token|secret|api[_-]?key)\s*([=:])\s*([^\s,;]+)"
)
_SENSITIVE_KEY_PATTERN = re.compile(
    r"(?i)(password|passwd|passphrase|credential|private[_-]?key|identity[_-]?file|"
    r"api[_-]?key|access[_-]?token|refresh[_-]?token|potcar[_-]?(content|body|text))"
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sanitize_text(value: str) -> str:
    result = _BEARER_PATTERN.sub("Bearer [REDACTED]", value)
    result = _SECRET_ASSIGNMENT_PATTERN.sub(r"\1\2[REDACTED]", result)
    if _PRIVATE_KEY_PATTERN.search(result):
        return "[REDACTED PRIVATE KEY MATERIAL]"
    return result


def sanitize_record_value(value: Any, *, key: str | None = None) -> Any:
    """Redact credentials and restricted file bodies before persistence."""
    if key and _SENSITIVE_KEY_PATTERN.search(str(key)):
        return "[REDACTED]"
    if isinstance(value, str):
        return _sanitize_text(value)
    if isinstance(value, dict):
        return {
            str(item_key): sanitize_record_value(item_value, key=str(item_key))
            for item_key, item_value in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [sanitize_record_value(item) for item in value]
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.stem}.", suffix=".tmp", dir=str(path.parent))
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(str(temp_path), str(path))
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


@contextmanager
def _store_lock(records_path: Path) -> Iterator[None]:
    records_path.parent.mkdir(parents=True, exist_ok=True)
    with records_path.open("a+", encoding="utf-8") as handle:
        try:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        except (ImportError, OSError):
            pass
        try:
            yield
        finally:
            try:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except (ImportError, OSError):
                pass


def _paths(root: Path) -> dict[str, Path]:
    simflow_dir = root / ".simflow"
    return {
        "simflow": simflow_dir,
        "project": simflow_dir / "project.json",
        "records": simflow_dir / "records.jsonl",
        "checkpoints": simflow_dir / "checkpoints",
        "reports": simflow_dir / "reports",
        "legacy_state": simflow_dir / "state",
    }


def _empty_project(root: Path, *, created_at: str | None = None) -> dict[str, Any]:
    now = _now()
    project_hash = hashlib.sha256(str(root).encode("utf-8")).hexdigest()[:12]
    return {
        "schema_version": PROJECT_SCHEMA,
        "project_id": f"project_{project_hash}",
        "project_root": str(root),
        "created_at": created_at or now,
        "updated_at": now,
        "current": {
            "goal": None,
            "active_run_id": None,
            "latest_milestone_id": None,
            "latest_failure_id": None,
            "latest_checkpoint_id": None,
            "next_action": None,
        },
        "counts": {"total": 0, "by_kind": {}},
        "last_record": None,
    }


def _read_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return default


def _read_records(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                records.append(payload)
    return records


def _normalize_path_refs(root: Path, refs: list[Any] | None) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for raw in refs or []:
        ref = {"path": raw} if isinstance(raw, str) else dict(raw)
        path_value = ref.get("path")
        restricted = bool(ref.get("restricted"))
        if path_value:
            resolved = resolve_project_path(path_value, project_root=str(root))
            if restricted:
                ref["path"] = "[RESTRICTED PATH]"
                ref.setdefault("name", resolved.name)
            else:
                ref["path"] = str(resolved.relative_to(root))
            if resolved.is_file() and not ref.get("sha256"):
                ref["sha256"] = _sha256(resolved)
            if resolved.is_file() and not ref.get("size_bytes"):
                ref["size_bytes"] = resolved.stat().st_size
            ref["exists"] = resolved.exists()
        normalized.append(sanitize_record_value(ref))
    return normalized


def _append_record(path: Path, record: dict[str, Any]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = (_canonical_json(record) + "\n").encode("utf-8")
    with path.open("ab") as handle:
        offset = handle.tell()
        handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())
    return offset


def _load_project(root: Path, paths: dict[str, Path]) -> dict[str, Any]:
    payload = _read_json(paths["project"], {})
    if isinstance(payload, dict) and payload.get("schema_version") == PROJECT_SCHEMA:
        return payload
    return _empty_project(root)


def _update_project(project: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    updated = json.loads(json.dumps(project))
    updated["updated_at"] = record["created_at"]
    counts = updated.setdefault("counts", {"total": 0, "by_kind": {}})
    counts["total"] = int(counts.get("total", 0)) + 1
    by_kind = counts.setdefault("by_kind", {})
    by_kind[record["kind"]] = int(by_kind.get(record["kind"], 0)) + 1
    updated["last_record"] = {
        "record_id": record["record_id"],
        "kind": record["kind"],
        "status": record.get("status"),
        "summary": record["summary"],
        "created_at": record["created_at"],
    }
    current = updated.setdefault("current", {})
    if record.get("goal") is not None:
        current["goal"] = record.get("goal")
    if record.get("next_action") is not None:
        current["next_action"] = record.get("next_action")
    if record["kind"] == "milestone":
        current["latest_milestone_id"] = record["record_id"]
    if record["kind"] == "failure":
        current["latest_failure_id"] = record["record_id"]
    if record["kind"] == "checkpoint":
        current["latest_checkpoint_id"] = record.get("checkpoint_id")
    if record["kind"] == "run":
        status = str(record.get("status") or "").lower()
        run_id = record.get("run_id")
        if status in ACTIVE_RUN_STATUSES:
            current["active_run_id"] = run_id
        elif status in TERMINAL_RUN_STATUSES and current.get("active_run_id") == run_id:
            current["active_run_id"] = None
    return updated


def record_event(
    project_root: str,
    *,
    kind: str,
    summary: str,
    status: str | None = None,
    stage: str | None = None,
    run_id: str | None = None,
    goal: str | None = None,
    next_action: Any = None,
    artifacts: list[Any] | None = None,
    parent_ids: list[str] | None = None,
    details: dict[str, Any] | None = None,
    record_id: str | None = None,
    checkpoint_id: str | None = None,
) -> dict[str, Any]:
    """Append one logical project event and refresh the compact summary."""
    root = resolve_project_root(project_root=project_root)
    normalized_kind = str(kind).strip().lower()
    if normalized_kind not in RECORD_KINDS:
        raise ValueError(f"Unsupported record kind: {kind}")
    if not str(summary).strip():
        raise ValueError("summary is required")
    if normalized_kind == "run" and not run_id:
        run_id = _id("run")

    paths = _paths(root)
    record = {
        "schema_version": RECORD_SCHEMA,
        "record_id": record_id or _id("rec"),
        "kind": normalized_kind,
        "summary": _sanitize_text(str(summary).strip()),
        "status": str(status).strip().lower() if status is not None else None,
        "stage": str(stage).strip() if stage else None,
        "run_id": run_id,
        "goal": _sanitize_text(str(goal)) if goal else None,
        "next_action": sanitize_record_value(next_action),
        "artifacts": _normalize_path_refs(root, artifacts),
        "parent_ids": list(parent_ids or []),
        "details": sanitize_record_value(details or {}),
        "checkpoint_id": checkpoint_id,
        "created_at": _now(),
    }
    record = {key: value for key, value in record.items() if value not in (None, [], {})}

    with _store_lock(paths["records"]):
        project = _load_project(root, paths)
        offset = _append_record(paths["records"], record)
        record["records_offset"] = offset
        project = _update_project(project, record)
        _write_json_atomic(paths["project"], project)
    return record


def _legacy_summary(paths: dict[str, Path]) -> dict[str, Any]:
    state_dir = paths["legacy_state"]
    if not state_dir.is_dir():
        return {"detected": False, "state_files": [], "counts": {}}
    files = sorted(path.name for path in state_dir.glob("*.json") if path.is_file())
    counts: dict[str, int] = {}
    for name in ("artifacts.json", "checkpoints.json", "gates.json", "jobs.json"):
        payload = _read_json(state_dir / name, [])
        if isinstance(payload, list):
            counts[name.removesuffix(".json")] = len(payload)
    return {"detected": bool(files), "state_files": files, "counts": counts}


def inspect_project(
    project_root: str,
    *,
    kind: str | None = None,
    status: str | None = None,
    record_id: str | None = None,
    run_id: str | None = None,
    limit: int = 20,
    include_legacy: bool = True,
) -> dict[str, Any]:
    """Read compact project status and filtered recent records without writing."""
    root = resolve_project_root(project_root=project_root)
    paths = _paths(root)
    records = _read_records(paths["records"])
    filtered = records
    if kind:
        filtered = [item for item in filtered if item.get("kind") == kind]
    if status:
        filtered = [item for item in filtered if item.get("status") == status]
    if record_id:
        filtered = [item for item in filtered if item.get("record_id") == record_id]
    if run_id:
        filtered = [item for item in filtered if item.get("run_id") == run_id]
    bounded_limit = max(1, min(int(limit), 200))
    project = _read_json(paths["project"], None)
    result = {
        "initialized": isinstance(project, dict) and project.get("schema_version") == PROJECT_SCHEMA,
        "project": project,
        "records": filtered[-bounded_limit:],
        "record_count": len(records),
        "matched_count": len(filtered),
        "paths": {
            "project": ".simflow/project.json",
            "records": ".simflow/records.jsonl",
            "checkpoints": ".simflow/checkpoints",
        },
    }
    if include_legacy:
        result["legacy"] = _legacy_summary(paths)
    return result


def create_recovery_checkpoint(
    project_root: str,
    *,
    summary: str,
    status: str = "ready",
    record_id: str | None = None,
    run_id: str | None = None,
    milestone_id: str | None = None,
    input_refs: list[Any] | None = None,
    restart_refs: list[Any] | None = None,
    resume_command: str | None = None,
    risk_notes: list[str] | None = None,
) -> dict[str, Any]:
    """Create a compact recovery reference without copying workflow registries."""
    root = resolve_project_root(project_root=project_root)
    normalized_status = str(status).strip().lower()
    if normalized_status not in CHECKPOINT_STATUSES:
        raise ValueError(f"Unsupported checkpoint status: {status}")
    if normalized_status != "diagnostic" and not any(
        (record_id, run_id, milestone_id, input_refs, restart_refs, resume_command)
    ):
        raise ValueError("A recoverable checkpoint requires at least one recovery reference")

    paths = _paths(root)
    checkpoint_id = _id("ckpt")
    checkpoint_path = paths["checkpoints"] / f"{checkpoint_id}.json"
    with _store_lock(paths["records"]):
        records_offset = paths["records"].stat().st_size if paths["records"].is_file() else 0
        checkpoint = {
            "schema_version": CHECKPOINT_SCHEMA,
            "checkpoint_id": checkpoint_id,
            "summary": _sanitize_text(str(summary).strip()),
            "status": normalized_status,
            "record_id": record_id,
            "run_id": run_id,
            "milestone_id": milestone_id,
            "records_offset": records_offset,
            "input_refs": _normalize_path_refs(root, input_refs),
            "restart_refs": _normalize_path_refs(root, restart_refs),
            "resume_command": _sanitize_text(resume_command) if resume_command else None,
            "risk_notes": sanitize_record_value(risk_notes or []),
            "created_at": _now(),
        }
        checkpoint = {key: value for key, value in checkpoint.items() if value not in (None, [], {})}
        _write_json_atomic(checkpoint_path, checkpoint)
        try:
            record = {
                "schema_version": RECORD_SCHEMA,
                "record_id": _id("rec"),
                "kind": "checkpoint",
                "summary": checkpoint["summary"],
                "status": normalized_status,
                "run_id": run_id,
                "checkpoint_id": checkpoint_id,
                "details": {"path": str(checkpoint_path.relative_to(root)), "records_offset": records_offset},
                "created_at": checkpoint["created_at"],
            }
            record = {key: value for key, value in record.items() if value not in (None, [], {})}
            _append_record(paths["records"], record)
            project = _update_project(_load_project(root, paths), record)
            _write_json_atomic(paths["project"], project)
        except Exception:
            checkpoint_path.unlink(missing_ok=True)
            raise
    return checkpoint


def _validate_checkpoint_ref(root: Path, ref: dict[str, Any], role: str) -> dict[str, Any]:
    path_value = ref.get("path")
    if not path_value or path_value == "[RESTRICTED PATH]":
        return {"role": role, "path": path_value, "status": "metadata_only"}
    try:
        resolved = resolve_project_path(path_value, project_root=str(root))
    except ProjectRootError as error:
        return {"role": role, "path": path_value, "status": "invalid", "message": str(error)}
    if not resolved.exists():
        return {"role": role, "path": path_value, "status": "missing"}
    expected = ref.get("sha256")
    if expected and resolved.is_file():
        actual = _sha256(resolved)
        if actual != expected:
            return {
                "role": role,
                "path": path_value,
                "status": "hash_mismatch",
                "expected_sha256": expected,
                "actual_sha256": actual,
            }
    return {"role": role, "path": path_value, "status": "ready"}


def recover_checkpoint(project_root: str, *, checkpoint_id: str | None = None) -> dict[str, Any]:
    """Inspect a compact checkpoint and validate its recovery references."""
    root = resolve_project_root(project_root=project_root)
    paths = _paths(root)
    if not checkpoint_id:
        project = _read_json(paths["project"], {})
        checkpoint_id = project.get("current", {}).get("latest_checkpoint_id")
    if not checkpoint_id:
        raise FileNotFoundError("No checkpoint is available")
    if Path(checkpoint_id).name != checkpoint_id:
        raise ValueError("Invalid checkpoint_id")
    checkpoint_path = paths["checkpoints"] / f"{checkpoint_id}.json"
    checkpoint = _read_json(checkpoint_path, None)
    if not isinstance(checkpoint, dict):
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_id}")

    checks = [
        _validate_checkpoint_ref(root, ref, "input")
        for ref in checkpoint.get("input_refs", [])
        if isinstance(ref, dict)
    ]
    checks.extend(
        _validate_checkpoint_ref(root, ref, "restart")
        for ref in checkpoint.get("restart_refs", [])
        if isinstance(ref, dict)
    )
    blocking = [item for item in checks if item["status"] in {"missing", "invalid", "hash_mismatch"}]
    return {
        "checkpoint": checkpoint,
        "ready": checkpoint.get("status") != "diagnostic" and not blocking,
        "checks": checks,
        "issues": blocking,
        "resume_command": checkpoint.get("resume_command"),
        "note": "Recovery validates references and returns the restart instruction; it does not execute compute.",
    }
