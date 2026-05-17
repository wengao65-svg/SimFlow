"""Artifact management with versioning and lineage."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .state import ensure_workflow_initialized, resolve_project_root

ARTIFACTS_DIR = ".simflow/artifacts"
STATE_FILE = ".simflow/state/artifacts.json"


def _compute_checksum(file_path: str) -> str:
    """Compute SHA256 checksum of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


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


def register_artifact(
    name: str,
    artifact_type: str,
    stage: str,
    base_dir: str = ".",
    path: Optional[str] = None,
    parent_artifacts: Optional[list] = None,
    parameters: Optional[dict] = None,
    software: Optional[str] = None,
    project_root: Optional[str] = None,
) -> dict:
    """Register a new artifact."""
    import uuid
    root = resolve_project_root(project_root=project_root, base_dir=base_dir)
    ensure_workflow_initialized(project_root=str(root))
    artifacts = _read_artifacts(project_root=str(root))
    now = datetime.now(timezone.utc).isoformat()
    art_id = f"art_{uuid.uuid4().hex[:8]}"

    # Determine version
    existing = [a for a in artifacts if a["name"] == name]
    major = len(existing) + 1
    version = f"v{major}.0.0"

    # Compute checksum if file exists
    checksum = None
    if path:
        artifact_path = Path(path)
        full_path = artifact_path if artifact_path.is_absolute() else root / artifact_path
        if full_path.exists():
            checksum = _compute_checksum(str(full_path))

    artifact = {
        "artifact_id": art_id,
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
        "checksum": checksum,
        "created_at": now,
    }
    artifacts.append(artifact)
    _write_artifacts(artifacts, project_root=str(root))
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
