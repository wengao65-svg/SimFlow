"""Compact checkpoint compatibility adapter.

New checkpoints contain recovery references only. Legacy snapshot checkpoints
can be listed for migration, but they are never restored into active state.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from .records import create_recovery_checkpoint, recover_checkpoint
from .result_contract import attach_simflow_result
from .state import resolve_project_root


CHECKPOINTS_DIR = ".simflow/checkpoints"
_STATUS_TO_COMPACT = {"success": "ready", "partial": "partial", "failure": "diagnostic"}
_STATUS_FROM_COMPACT = {"ready": "success", "partial": "partial", "diagnostic": "failure"}


def _attach(checkpoint: dict[str, Any], *, activity: str, state_effect: str = "checkpoint_admin") -> dict[str, Any]:
    return attach_simflow_result(
        checkpoint,
        role="state_admin",
        activity=activity,
        legacy_status=checkpoint.get("status", "success"),
        stage=checkpoint.get("stage_id"),
        state_effect=state_effect,
    )


def _compact_view(payload: dict[str, Any], *, workflow_id: str | None = None, stage_id: str | None = None) -> dict[str, Any]:
    compact_status = payload.get("status", "diagnostic")
    view = {
        **payload,
        "workflow_id": payload.get("workflow_id") or workflow_id,
        "stage_id": payload.get("stage_id") or stage_id,
        "status": _STATUS_FROM_COMPACT.get(compact_status, compact_status),
        "recovery_status": compact_status,
        "recoverable": compact_status != "diagnostic",
        "path": str(Path(CHECKPOINTS_DIR) / f"{payload.get('checkpoint_id')}.json"),
        "storage": "compact_reference",
    }
    view.pop("schema_version", None)
    return view


def _load_checkpoint_file(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("schema_version") == "simflow.checkpoint.v1":
        return _compact_view(payload)
    return {
        **payload,
        "storage": "legacy_snapshot",
        "legacy_read_only": True,
        "recoverable": False,
    }


def create_checkpoint(
    workflow_id: str,
    stage_id: str,
    description: str,
    base_dir: str = ".",
    status: str = "success",
    job_id: Optional[str] = None,
    project_root: Optional[str] = None,
    failure_context: Optional[dict[str, Any]] = None,
    session_context_id: Optional[str] = None,
    experiment_id: Optional[str] = None,
    iteration_id: Optional[str] = None,
    activity_id: Optional[str] = None,
    *,
    record_id: Optional[str] = None,
    run_id: Optional[str] = None,
    milestone_id: Optional[str] = None,
    input_refs: Optional[list[Any]] = None,
    restart_refs: Optional[list[Any]] = None,
    resume_command: Optional[str] = None,
    risk_notes: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Create a compact recovery reference through the legacy Python API."""
    del session_context_id, experiment_id, iteration_id, activity_id
    normalized = str(status).strip().lower()
    if normalized not in _STATUS_TO_COMPACT:
        raise ValueError(f"Unsupported checkpoint status: {status}")
    root = resolve_project_root(project_root=project_root, base_dir=base_dir)
    effective_run_id = run_id or job_id
    compact_status = _STATUS_TO_COMPACT[normalized]
    notes = list(risk_notes or [])
    if failure_context:
        notes.append(f"Failure context: {failure_context.get('message') or failure_context.get('reason_code') or 'recorded'}")
    if compact_status != "diagnostic" and not any(
        (record_id, effective_run_id, milestone_id, input_refs, restart_refs, resume_command)
    ):
        compact_status = "diagnostic"
        notes.append("Legacy stage-boundary checkpoint had no restart reference and is diagnostic only.")

    payload = create_recovery_checkpoint(
        str(root),
        summary=description or f"{stage_id} recovery point",
        status=compact_status,
        record_id=record_id,
        run_id=effective_run_id,
        milestone_id=milestone_id,
        input_refs=input_refs,
        restart_refs=restart_refs,
        resume_command=resume_command,
        risk_notes=notes,
    )
    payload["workflow_id"] = workflow_id
    payload["stage_id"] = stage_id
    payload["job_id"] = job_id
    checkpoint_path = root / CHECKPOINTS_DIR / f"{payload['checkpoint_id']}.json"
    checkpoint_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    view = _compact_view(payload, workflow_id=workflow_id, stage_id=stage_id)
    view["status"] = normalized if compact_status != "diagnostic" or normalized == "failure" else "failure"
    return _attach(view, activity="create_checkpoint")


def list_checkpoints(base_dir: str = ".", project_root: Optional[str] = None) -> list[dict[str, Any]]:
    """List compact checkpoints and read-only legacy snapshot files."""
    root = resolve_project_root(project_root=project_root, base_dir=base_dir)
    checkpoint_dir = root / CHECKPOINTS_DIR
    checkpoints = []
    if checkpoint_dir.is_dir():
        for path in checkpoint_dir.glob("*.json"):
            checkpoint = _load_checkpoint_file(path)
            if checkpoint is not None:
                checkpoints.append(_attach(checkpoint, activity="list_checkpoints", state_effect="none"))
    seen = {checkpoint.get("checkpoint_id") for checkpoint in checkpoints}
    registry_path = root / ".simflow" / "state" / "checkpoints.json"
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8")) if registry_path.is_file() else []
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        registry = []
    for entry in registry if isinstance(registry, list) else []:
        if not isinstance(entry, dict) or entry.get("checkpoint_id") in seen:
            continue
        checkpoints.append(_attach({
            **entry,
            "storage": "legacy_registry",
            "legacy_read_only": True,
            "recoverable": False,
        }, activity="list_checkpoints", state_effect="none"))
    return sorted(checkpoints, key=lambda item: (item.get("created_at", ""), item.get("checkpoint_id", "")))


def restore_checkpoint(
    checkpoint_id: str,
    base_dir: str = ".",
    project_root: Optional[str] = None,
    **_: Any,
) -> dict[str, Any]:
    """Validate compact recovery references without rolling back state files."""
    root = resolve_project_root(project_root=project_root, base_dir=base_dir)
    path = root / CHECKPOINTS_DIR / f"{checkpoint_id}.json"
    checkpoint = _load_checkpoint_file(path) if path.is_file() else None
    if checkpoint is None:
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_id}")
    if checkpoint.get("storage") == "legacy_snapshot":
        raise ValueError(
            f"Legacy checkpoint {checkpoint_id} is read-only; generate an explicit compact recovery reference"
        )
    if checkpoint.get("recovery_status") == "diagnostic":
        raise ValueError(f"Checkpoint {checkpoint_id} is diagnostic-only and cannot be recovered")
    validation = recover_checkpoint(str(root), checkpoint_id=checkpoint_id)
    result = {**checkpoint, "recovery_validation": validation, "state_restored": False}
    return _attach(result, activity="restore_checkpoint")


def get_latest_checkpoint(
    base_dir: str = ".",
    project_root: Optional[str] = None,
    *,
    status: Optional[str] = None,
    recoverable_only: bool = False,
    experiment_id: Optional[str] = None,
    iteration_id: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """Return the latest checkpoint matching compact recovery filters."""
    del experiment_id, iteration_id
    checkpoints = list_checkpoints(base_dir, project_root=project_root)
    if status is not None:
        checkpoints = [checkpoint for checkpoint in checkpoints if checkpoint.get("status") == status]
    if recoverable_only:
        checkpoints = [checkpoint for checkpoint in checkpoints if checkpoint.get("recoverable")]
    return checkpoints[-1] if checkpoints else None


def get_latest_recovery_checkpoint(
    base_dir: str = ".",
    project_root: Optional[str] = None,
    *,
    experiment_id: Optional[str] = None,
    iteration_id: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    del experiment_id, iteration_id
    checkpoints = [
        checkpoint
        for checkpoint in list_checkpoints(base_dir, project_root=project_root)
        if checkpoint.get("recoverable") and checkpoint.get("status") in {"success", "partial"}
    ]
    return checkpoints[-1] if checkpoints else None
