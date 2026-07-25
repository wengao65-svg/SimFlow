"""Checkpoint management for workflow recovery."""

import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .result_contract import attach_simflow_result
from .state import (
    CANONICAL_ARTIFACT_STAGE_DIRS,
    CHECKPOINT_STATUSES,
    ensure_workflow_initialized,
    read_state,
    resolve_project_root,
    touch_workflow,
)

CHECKPOINTS_DIR = ".simflow/checkpoints"
STATE_DIR = ".simflow/state"
_ORIGINAL_OS_REPLACE = os.replace


def _checkpoint_registry_entry(
    *,
    checkpoint_id: str,
    workflow_id: str,
    stage_id: str,
    description: str,
    status: str,
    created_at: str,
    job_id: Optional[str],
) -> dict[str, Any]:
    return {
        "checkpoint_id": checkpoint_id,
        "workflow_id": workflow_id,
        "stage_id": stage_id,
        "job_id": job_id,
        "description": description,
        "status": status,
        "path": str(Path(CHECKPOINTS_DIR) / f"{checkpoint_id}.json"),
        "created_at": created_at,
    }


def _load_checkpoint_registry(root: Path) -> list[dict[str, Any]]:
    payload = read_state(project_root=str(root), state_file="checkpoints.json")
    return payload if isinstance(payload, list) else []


def _write_temp_json(target_path: Path, data: Any) -> Path:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{target_path.stem}.",
        suffix=".tmp",
        dir=str(target_path.parent),
    )
    temp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
        return temp_path
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def _replace_file(temp_path: Path, target_path: Path, *, replace_fn=os.replace) -> None:
    try:
        replace_fn(str(temp_path), str(target_path))
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def _write_json_atomic(target_path: Path, data: Any, *, replace_fn=os.replace) -> None:
    temp_path = _write_temp_json(target_path, data)
    _replace_file(temp_path, target_path, replace_fn=replace_fn)


def _restore_checkpoint_state(root: Path, *, stages: dict[str, Any], registry: list[dict[str, Any]]) -> None:
    _write_json_atomic(root / STATE_DIR / "stages.json", stages, replace_fn=_ORIGINAL_OS_REPLACE)
    _write_json_atomic(root / STATE_DIR / "checkpoints.json", registry, replace_fn=_ORIGINAL_OS_REPLACE)


def _snapshot_state(root: Path) -> dict[str, Any]:
    state_snapshot: dict[str, Any] = {}
    state_path = root / STATE_DIR
    if state_path.exists():
        for path in state_path.glob("*.json"):
            with open(path, "r", encoding="utf-8") as handle:
                state_snapshot[path.name] = json.load(handle)
    return state_snapshot


def _artifact_versions_from_snapshot(state_snapshot: dict[str, Any]) -> dict[str, Any]:
    versions: dict[str, Any] = {}
    artifacts = state_snapshot.get("artifacts.json", [])
    if isinstance(artifacts, list):
        for artifact in artifacts:
            if isinstance(artifact, dict) and artifact.get("artifact_id"):
                versions[artifact["artifact_id"]] = artifact.get("version")
    return versions


def _attach_checkpoint_result(
    checkpoint: dict[str, Any],
    *,
    activity: str,
    stage_id: str | None = None,
    state_effect: str = "checkpoint_admin",
) -> dict[str, Any]:
    return attach_simflow_result(
        checkpoint,
        role="state_admin",
        activity=activity,
        legacy_status=checkpoint.get("status", "success"),
        stage=stage_id,
        state_effect=state_effect,
    )


def create_checkpoint(
    workflow_id: str,
    stage_id: str,
    description: str,
    base_dir: str = ".",
    status: str = "success",
    job_id: Optional[str] = None,
    project_root: Optional[str] = None,
    failure_context: Optional[dict[str, Any]] = None,
) -> dict:
    """Create a workflow checkpoint.

    P1.2: Auto-upserts the stage_id into stages.json if it's a canonical
    stage that hasn't been declared yet.
    P1.3: Enforces state_snapshot completeness for non-failure checkpoints.
    P1.4: Validates stage_id against canonical stages + already-declared
    custom stages. Failure checkpoints are exempt from stage_id validation.
    """
    import re
    import warnings

    normalized_status = str(status).strip().lower()
    if normalized_status not in CHECKPOINT_STATUSES:
        raise ValueError(f"Unsupported checkpoint status: {status}")

    root = resolve_project_root(project_root=project_root, base_dir=base_dir)
    ensure_workflow_initialized(project_root=str(root))
    ckpt_dir = root / CHECKPOINTS_DIR
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    # P1.4: Validate stage_id
    is_canonical = stage_id in CANONICAL_ARTIFACT_STAGE_DIRS
    stages = read_state(project_root=str(root), state_file="stages.json")
    if not isinstance(stages, dict):
        stages = {}
    stage_already_declared = stage_id in stages

    if not is_canonical and not stage_already_declared:
        if normalized_status != "failure":
            raise ValueError(
                f"stage_id '{stage_id}' is not a canonical stage "
                f"({', '.join(sorted(CANONICAL_ARTIFACT_STAGE_DIRS))}) "
                f"and was not declared via update_stage. "
                f"Call update_stage('{stage_id}', 'in_progress') first, "
                f"or use status='failure' for failure checkpoints."
            )
        else:
            warnings.warn(
                f"Checkpoint with non-canonical undeclared stage_id '{stage_id}' "
                f"(allowed because status='failure')",
                UserWarning,
                stacklevel=2,
            )

    # Generate checkpoint ID
    existing = list(ckpt_dir.glob("ckpt_*.json"))
    num = len(existing) + 1
    safe_stage = re.sub(r"[^a-z0-9]", "_", stage_id.lower())
    ckpt_id = f"ckpt_{num:03d}_{safe_stage}"

    now = datetime.now(timezone.utc).isoformat()
    registry = _load_checkpoint_registry(root)
    registry_entry = _checkpoint_registry_entry(
        checkpoint_id=ckpt_id,
        workflow_id=workflow_id,
        stage_id=stage_id,
        description=description,
        status=normalized_status,
        created_at=now,
        job_id=job_id,
    )
    updated_stages = json.loads(json.dumps(stages))

    # P1.2: Auto-upsert stage into stages.json if canonical but not yet declared
    stage_record = updated_stages.get(stage_id)
    if isinstance(stage_record, dict):
        if normalized_status == "failure":
            stage_record["failure_checkpoint_id"] = ckpt_id
        else:
            stage_record["checkpoint_id"] = ckpt_id
            if normalized_status == "success":
                stage_record["last_success_checkpoint_id"] = ckpt_id
    elif is_canonical:
        # Canonical stage not yet declared — auto-create it
        updated_stages[stage_id] = {
            "stage_name": stage_id,
            "status": "in_progress",
            "agent": None,
            "inputs": [],
            "outputs": [],
            "checkpoint_id": ckpt_id if normalized_status != "failure" else None,
            "failure_checkpoint_id": ckpt_id if normalized_status == "failure" else None,
            "last_success_checkpoint_id": ckpt_id if normalized_status == "success" else None,
            "error_message": None,
            "started_at": now,
            "completed_at": None,
        }
    elif stage_already_declared:
        # Already handled above
        pass

    updated_registry = [*registry, registry_entry]

    # P1.3: Enforce state_snapshot completeness for non-failure checkpoints
    state_snapshot = _snapshot_state(root)
    required_snapshot_files = {"workflow.json", "stages.json"}
    missing_snapshot = required_snapshot_files - set(state_snapshot.keys())
    recoverable = bool(state_snapshot) and not missing_snapshot
    if normalized_status != "failure":
        if not state_snapshot:
            raise ValueError(
                "state_snapshot is empty — cannot create a success/partial "
                "checkpoint without state to recover. Use status='failure' "
                "for failure checkpoints that may have incomplete state."
            )
        if missing_snapshot:
            raise ValueError(
                f"state_snapshot is missing required files: {missing_snapshot}. "
                f"Cannot create a recoverable checkpoint without them."
            )

    state_snapshot["stages.json"] = updated_stages
    state_snapshot["checkpoints.json"] = updated_registry
    artifact_versions = _artifact_versions_from_snapshot(state_snapshot)

    checkpoint = {
        "checkpoint_id": ckpt_id,
        "workflow_id": workflow_id,
        "stage_id": stage_id,
        "job_id": job_id,
        "description": description,
        "state_snapshot": state_snapshot,
        "artifact_versions": artifact_versions,
        "lineage_snapshot": state_snapshot.get("lineage.json", {"links": []}),
        "recoverable": recoverable,
        "failure_context": failure_context if normalized_status == "failure" else None,
        "status": normalized_status,
        "created_at": now,
    }
    _attach_checkpoint_result(checkpoint, activity="create_checkpoint", stage_id=stage_id)

    ckpt_file = ckpt_dir / f"{ckpt_id}.json"
    checkpoint_temp = _write_temp_json(ckpt_file, checkpoint)
    try:
        _write_json_atomic(root / STATE_DIR / "stages.json", updated_stages, replace_fn=os.replace)
        _write_json_atomic(root / STATE_DIR / "checkpoints.json", updated_registry, replace_fn=os.replace)
        _replace_file(checkpoint_temp, ckpt_file, replace_fn=os.replace)
    except Exception:
        checkpoint_temp.unlink(missing_ok=True)
        ckpt_file.unlink(missing_ok=True)
        _restore_checkpoint_state(root, stages=stages, registry=registry)
        raise

    # P1.5: Auto-propagate checkpoint creation to workflow.json/summary.json
    # so cross-session continuity works (fixes S6->S14 amnesia where
    # summary.json.updated_at stayed 4 days behind checkpoint creation).
    touch_workflow(str(root))

    return checkpoint


def list_checkpoints(base_dir: str = ".", project_root: Optional[str] = None) -> list:
    """List all checkpoints."""
    root = resolve_project_root(project_root=project_root, base_dir=base_dir)
    ckpt_dir = root / CHECKPOINTS_DIR
    if not ckpt_dir.exists():
        return []
    checkpoints = []
    registry = _load_checkpoint_registry(root)
    if registry:
        for entry in registry:
            if not isinstance(entry, dict):
                continue
            checkpoint_path = root / entry.get("path", "")
            if not checkpoint_path.is_file():
                checkpoint_path = ckpt_dir / f"{entry.get('checkpoint_id', '')}.json"
            if not checkpoint_path.is_file():
                checkpoint = dict(entry)
            else:
                with open(checkpoint_path, "r", encoding="utf-8") as handle:
                    checkpoint = json.load(handle)
            checkpoints.append(
                _attach_checkpoint_result(
                    checkpoint,
                    activity="list_checkpoints",
                    stage_id=checkpoint.get("stage_id"),
                    state_effect="none",
                )
            )
        return checkpoints

    for path in sorted(ckpt_dir.glob("ckpt_*.json")):
        with open(path, "r", encoding="utf-8") as handle:
            checkpoint = json.load(handle)
        checkpoints.append(
            _attach_checkpoint_result(
                checkpoint,
                activity="list_checkpoints",
                stage_id=checkpoint.get("stage_id"),
                state_effect="none",
            )
        )
    return checkpoints


def _snapshot_state_bytes(state_dir: Path) -> dict[str, bytes]:
    if not state_dir.exists():
        return {}
    return {
        path.name: path.read_bytes()
        for path in sorted(state_dir.glob("*.json"))
        if path.is_file()
    }


def _validate_state_snapshot_name(name: str) -> str:
    path = Path(name)
    if path.name != name or path.suffix != ".json":
        raise ValueError(f"Invalid checkpoint state file name: {name}")
    return name


def _write_state_bytes_atomic(state_dir: Path, name: str, content: bytes) -> None:
    target = state_dir / name
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{target.stem}.rollback.",
        suffix=".tmp",
        dir=str(target.parent),
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
        os.replace(str(tmp_path), str(target))
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def _restore_state_bytes(state_dir: Path, snapshot: dict[str, bytes]) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    for path in list(state_dir.glob("*.json")):
        if path.name not in snapshot:
            path.unlink()
    for name, content in snapshot.items():
        _write_state_bytes_atomic(state_dir, name, content)


def restore_checkpoint(checkpoint_id: str, base_dir: str = ".", project_root: Optional[str] = None) -> dict:
    """Restore workflow state from a checkpoint."""
    root = resolve_project_root(project_root=project_root, base_dir=base_dir)
    ckpt_file = root / CHECKPOINTS_DIR / f"{checkpoint_id}.json"
    if not ckpt_file.exists():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_id}")

    with open(ckpt_file, "r", encoding="utf-8") as f:
        checkpoint = json.load(f)
    if checkpoint.get("recoverable") is False:
        raise ValueError(
            f"Checkpoint {checkpoint_id} is diagnostic-only and cannot be restored"
        )

    state_dir = root / STATE_DIR
    state_dir.mkdir(parents=True, exist_ok=True)
    pre_restore_bytes = _snapshot_state_bytes(state_dir)
    staged_dir = Path(tempfile.mkdtemp(prefix=".checkpoint_restore.", dir=str(state_dir.parent)))
    snapshot = checkpoint["state_snapshot"]
    try:
        snapshot_names = {_validate_state_snapshot_name(name) for name in snapshot}
        for name, data in snapshot.items():
            staged_path = staged_dir / _validate_state_snapshot_name(name)
            with open(staged_path, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2, ensure_ascii=False)
            json.loads(staged_path.read_text(encoding="utf-8"))

        for name in snapshot_names:
            _replace_file(staged_dir / name, state_dir / name, replace_fn=_ORIGINAL_OS_REPLACE)
        for path in list(state_dir.glob("*.json")):
            if path.name not in snapshot_names:
                path.unlink()
    except Exception:
        _restore_state_bytes(state_dir, pre_restore_bytes)
        raise
    finally:
        shutil.rmtree(staged_dir, ignore_errors=True)

    return _attach_checkpoint_result(checkpoint, activity="restore_checkpoint", stage_id=checkpoint.get("stage_id"))


def get_latest_checkpoint(
    base_dir: str = ".",
    project_root: Optional[str] = None,
    *,
    status: Optional[str] = None,
    recoverable_only: bool = False,
) -> Optional[dict]:
    """Get the most recent checkpoint matching recovery filters."""
    checkpoints = list_checkpoints(base_dir, project_root=project_root)
    if status is not None:
        checkpoints = [checkpoint for checkpoint in checkpoints if checkpoint.get("status") == status]
    if recoverable_only:
        checkpoints = [checkpoint for checkpoint in checkpoints if checkpoint.get("recoverable", True)]
    if not checkpoints:
        return None
    return checkpoints[-1]


def get_latest_recovery_checkpoint(
    base_dir: str = ".",
    project_root: Optional[str] = None,
) -> Optional[dict]:
    """Return the latest successful recoverable checkpoint."""
    return get_latest_checkpoint(
        base_dir,
        project_root=project_root,
        status="success",
        recoverable_only=True,
    )
