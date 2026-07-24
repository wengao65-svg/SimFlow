"""Artifact management with versioning and lineage."""

import hashlib
import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .state import (
    CANONICAL_ARTIFACT_STAGE_DIRS,
    ensure_workflow_initialized,
    read_state,
    resolve_project_root,
    touch_workflow,
)

ARTIFACTS_DIR = ".simflow/artifacts"
STATE_FILE = ".simflow/state/artifacts.json"
_ORIGINAL_OS_REPLACE = os.replace


def _compute_checksum(file_path: str) -> str:
    """Compute SHA256 checksum of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _compute_directory_tree_hash(dir_path: Path) -> tuple[str, dict]:
    """Compute a tree hash for a directory and collect file statistics.

    Walks the directory recursively, sorts file paths, computes SHA256 for
    each file, and hashes its relative path, size, and content digest. Returns
    (tree_hash, stats_dict).

    stats_dict contains:
    - file_count: number of files
    - total_size_bytes: total size of all files
    - file_hashes: list of {path, sha256, size} for each file
    """
    file_entries = []
    total_size = 0
    for path in sorted(dir_path.rglob("*")):
        if path.is_file():
            sha = _compute_checksum(str(path))
            size = path.stat().st_size
            total_size += size
            rel_path = str(path.relative_to(dir_path))
            file_entries.append({"path": rel_path, "sha256": sha, "size": size})

    h = hashlib.sha256()
    for entry in file_entries:
        encoded = json.dumps(
            [entry["path"], entry["size"], entry["sha256"]],
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        h.update(len(encoded).to_bytes(8, "big"))
        h.update(encoded)
    tree_hash = h.hexdigest()

    stats = {
        "file_count": len(file_entries),
        "total_size_bytes": total_size,
        "file_hashes": file_entries,
    }
    return tree_hash, stats


def _read_artifacts(base_dir: str = ".", project_root: Optional[str] = None) -> list:
    """Read the artifacts registry."""
    root = resolve_project_root(project_root=project_root, base_dir=base_dir)
    path = root / STATE_FILE
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_artifacts(artifacts: list, base_dir: str = ".", project_root: Optional[str] = None) -> None:
    """Write the artifacts registry."""
    root = resolve_project_root(project_root=project_root, base_dir=base_dir)
    ensure_workflow_initialized(project_root=str(root))
    path = root / STATE_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(artifacts, f, indent=2, ensure_ascii=False)


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


def _restore_file(path: Path, previous: Optional[bytes]) -> None:
    if previous is None:
        path.unlink(missing_ok=True)
        return
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.stem}.rollback.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    temp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(previous)
        _ORIGINAL_OS_REPLACE(str(temp_path), str(path))
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def _write_registration_transaction(root: Path, updates: dict[str, Any]) -> None:
    """Replace artifact-related state together and roll back partial writes."""
    state_dir = root / ".simflow" / "state"
    targets = {name: state_dir / name for name in updates}
    previous = {
        name: path.read_bytes() if path.exists() else None
        for name, path in targets.items()
    }
    temps: dict[str, Path] = {}
    try:
        for name, data in updates.items():
            temps[name] = _write_temp_json(targets[name], data)
    except Exception:
        for temp_path in temps.values():
            temp_path.unlink(missing_ok=True)
        raise
    replaced: list[str] = []
    try:
        for name in ("artifacts.json", "lineage.json", "stages.json"):
            os.replace(str(temps[name]), str(targets[name]))
            replaced.append(name)
    except Exception:
        for temp_path in temps.values():
            temp_path.unlink(missing_ok=True)
        for name in reversed(replaced):
            _restore_file(targets[name], previous[name])
        raise


def _updated_lineage_state(root: Path, artifact: dict, now: str) -> dict:
    lineage_state = read_state(project_root=str(root), state_file="lineage.json")
    if not isinstance(lineage_state, dict):
        lineage_state = {}
    nodes = list(lineage_state.get("artifacts", []))
    links = list(lineage_state.get("links", []))
    nodes.append({
        "artifact_id": artifact["artifact_id"],
        "workflow_id": artifact["workflow_id"],
        "name": artifact.get("name"),
        "type": artifact.get("type"),
        "stage": artifact.get("stage"),
        "version": artifact.get("version"),
        "path": artifact.get("path"),
        "checksum": artifact.get("checksum"),
        "updated_at": now,
    })
    for parent_id in artifact.get("lineage", {}).get("parent_artifacts", []):
        links.append({
            "link_id": f"lin_{uuid.uuid4().hex[:8]}",
            "child_artifact_id": artifact["artifact_id"],
            "parent_artifact_id": parent_id,
            "relationship": "derived_from",
            "stage": artifact.get("stage"),
            "parameters": artifact.get("lineage", {}).get("parameters", {}),
            "created_at": now,
        })
    return {**lineage_state, "artifacts": nodes, "links": links}


def _updated_stage_state(
    root: Path,
    stage: str,
    artifact_id: str,
    now: str,
    *,
    sync_stage_outputs: bool,
) -> dict:
    stages = read_state(project_root=str(root), state_file="stages.json")
    if not isinstance(stages, dict):
        stages = {}
    if not sync_stage_outputs:
        return stages
    if stage not in stages:
        stages[stage] = {
            "stage_name": stage,
            "status": "pending",
            "agent": None,
            "inputs": [],
            "outputs": [],
            "checkpoint_id": None,
            "failure_checkpoint_id": None,
            "last_success_checkpoint_id": None,
            "error_message": None,
            "error_report_artifact_id": None,
            "started_at": None,
            "completed_at": None,
        }
        if stage not in CANONICAL_ARTIFACT_STAGE_DIRS:
            stages[stage]["custom_stage"] = True
    outputs = list(stages[stage].get("outputs", []))
    if artifact_id not in outputs:
        outputs.append(artifact_id)
    stages[stage]["outputs"] = outputs
    stages[stage]["updated_at"] = now
    return stages


def register_artifact(
    name: str,
    artifact_type: str,
    stage: str,
    base_dir: str = ".",
    path: Optional[str] = None,
    parent_artifacts: Optional[list] = None,
    parameters: Optional[dict] = None,
    software: Optional[str] = None,
    metadata: Optional[dict] = None,
    project_root: Optional[str] = None,
    sync_stage_outputs: bool = True,
) -> dict:
    """Register a new artifact."""
    root = resolve_project_root(project_root=project_root, base_dir=base_dir)
    workflow = ensure_workflow_initialized(project_root=str(root))
    artifacts = _read_artifacts(project_root=str(root))
    now = datetime.now(timezone.utc).isoformat()
    art_id = f"art_{uuid.uuid4().hex[:8]}"

    # Determine version
    existing = [a for a in artifacts if a["name"] == name]
    major = len(existing) + 1
    version = f"v{major}.0.0"

    # Compute checksum if path exists (file or directory)
    checksum = None
    artifact_metadata = metadata or {}
    if path:
        artifact_path = Path(path)
        full_path = artifact_path if artifact_path.is_absolute() else root / artifact_path
        if full_path.is_dir():
            # Directory artifact: compute tree hash
            tree_hash, dir_stats = _compute_directory_tree_hash(full_path)
            checksum = tree_hash
            artifact_metadata = {
                **artifact_metadata,
                "is_directory": True,
                "file_count": dir_stats["file_count"],
                "total_size_bytes": dir_stats["total_size_bytes"],
                "tree_hash": tree_hash,
                "tree_hash_algorithm": "sha256-path-size-content-v1",
            }
        elif full_path.exists():
            # File artifact: compute single-file checksum
            checksum = _compute_checksum(str(full_path))

    artifact = {
        "artifact_id": art_id,
        "workflow_id": workflow["workflow_id"],
        "name": name,
        "type": artifact_type,
        "version": version,
        "stage": stage,
        "path": path,
        "lineage": {
            "parent_artifacts": parent_artifacts or [],
            "parameters": parameters or {},
            "software": software,
        },
        "metadata": artifact_metadata,
        "checksum": checksum,
        "created_at": now,
    }
    _write_registration_transaction(root, {
        "artifacts.json": [*artifacts, artifact],
        "lineage.json": _updated_lineage_state(root, artifact, now),
        "stages.json": _updated_stage_state(
            root,
            stage,
            art_id,
            now,
            sync_stage_outputs=sync_stage_outputs,
        ),
    })
    # Auto-refresh workflow.json/summary.json/status_summary.md
    touch_workflow(str(root))
    return artifact


def get_artifact(artifact_id: str, base_dir: str = ".", project_root: Optional[str] = None) -> Optional[dict]:
    """Get an artifact by ID."""
    artifacts = _read_artifacts(base_dir, project_root=project_root)
    for a in artifacts:
        if a["artifact_id"] == artifact_id:
            return a
    return None


def list_artifacts(stage: Optional[str] = None, base_dir: str = ".", project_root: Optional[str] = None) -> list:
    """List artifacts, optionally filtered by stage."""
    artifacts = _read_artifacts(base_dir, project_root=project_root)
    if stage:
        return [a for a in artifacts if a["stage"] == stage]
    return artifacts
