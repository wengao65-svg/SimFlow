"""Logical deliverable compatibility adapter.

New artifact writes are single compact records. Legacy artifact registries are
read-only inputs retained for old projects; this module never synchronizes
lineage, stages, summaries, or checkpoint snapshots.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path
from typing import Any, Optional

from .records import list_project_records, record_event
from .state import ProjectRootError, read_state, resolve_project_path, resolve_project_root


def _compute_checksum(file_path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(file_path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _compute_directory_tree_hash(directory: Path) -> tuple[str, dict[str, Any]]:
    entries = []
    total_size = 0
    for path in sorted(directory.rglob("*")):
        if not path.is_file():
            continue
        size = path.stat().st_size
        sha256 = _compute_checksum(path)
        total_size += size
        entries.append({"path": str(path.relative_to(directory)), "sha256": sha256, "size": size})
    digest = hashlib.sha256()
    for entry in entries:
        payload = json.dumps(
            [entry["path"], entry["size"], entry["sha256"]],
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    tree_hash = digest.hexdigest()
    return tree_hash, {
        "is_directory": True,
        "file_count": len(entries),
        "total_size_bytes": total_size,
        "tree_hash": tree_hash,
        "tree_hash_algorithm": "sha256-path-size-content-v1",
    }


def _legacy_artifacts(root: Path) -> list[dict[str, Any]]:
    path = root / ".simflow" / "state" / "artifacts.json"
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return []
    return payload if isinstance(payload, list) else []


def _read_artifacts(base_dir: str = ".", project_root: Optional[str] = None) -> list[dict[str, Any]]:
    """Compatibility alias for read-only artifact consumers."""
    return list_artifacts(base_dir=base_dir, project_root=project_root)


def _record_to_artifact(record: dict[str, Any]) -> dict[str, Any]:
    details = record.get("details", {}) if isinstance(record.get("details"), dict) else {}
    refs = record.get("artifacts", []) if isinstance(record.get("artifacts"), list) else []
    ref = refs[0] if refs and isinstance(refs[0], dict) else {}
    artifact_id = record.get("record_id")
    return {
        "artifact_id": artifact_id,
        "workflow_id": details.get("workflow_id"),
        "name": details.get("name") or record.get("summary"),
        "type": details.get("type") or "logical_deliverable",
        "version": details.get("version") or "v1.0.0",
        "stage": record.get("stage"),
        "path": ref.get("path"),
        "lineage": {
            "parent_artifacts": list(record.get("parent_ids", [])),
            "parameters": details.get("parameters", {}),
            "software": details.get("software"),
        },
        "metadata": details.get("metadata", {}),
        "checksum": ref.get("sha256"),
        "created_at": record.get("created_at"),
        "record_id": artifact_id,
        "storage": "compact_record",
    }


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
    session_context_id: Optional[str] = None,
    experiment_id: Optional[str] = None,
    iteration_id: Optional[str] = None,
    activity_id: Optional[str] = None,
) -> dict[str, Any]:
    """Record one logical deliverable without mutating legacy registries."""
    del sync_stage_outputs, session_context_id, experiment_id, iteration_id, activity_id
    root = resolve_project_root(project_root=project_root, base_dir=base_dir)
    artifact_id = f"art_{uuid.uuid4().hex[:12]}"
    artifact_metadata = dict(metadata or {})
    checksum = None
    artifact_ref = None
    if path:
        try:
            resolved = resolve_project_path(path, project_root=str(root))
            artifact_ref = {"path": str(resolved.relative_to(root)), "role": artifact_type}
        except ProjectRootError:
            resolved = Path(path).expanduser().resolve()
            artifact_ref = {"name": resolved.name, "role": artifact_type, "external_source": True}
        if resolved.is_dir():
            checksum, directory_metadata = _compute_directory_tree_hash(resolved)
            artifact_metadata = {**artifact_metadata, **directory_metadata}
            artifact_ref["sha256"] = checksum
            artifact_ref["manifest_kind"] = "directory_tree"
        elif resolved.is_file():
            checksum = _compute_checksum(resolved)
            artifact_ref["sha256"] = checksum
            artifact_ref["size_bytes"] = resolved.stat().st_size

    legacy_workflow = read_state(project_root=str(root), state_file="workflow.json")
    workflow_id = legacy_workflow.get("workflow_id") if isinstance(legacy_workflow, dict) else None
    if not workflow_id:
        workflow_id = f"project_{hashlib.sha256(str(root).encode('utf-8')).hexdigest()[:12]}"
    record = record_event(
        str(root),
        kind="artifact",
        summary=name,
        stage=stage,
        artifacts=[artifact_ref] if artifact_ref else None,
        parent_ids=list(parent_artifacts or []),
        details={
            "name": name,
            "type": artifact_type,
            "version": "v1.0.0",
            "workflow_id": workflow_id,
            "parameters": parameters or {},
            "software": software,
            "metadata": artifact_metadata,
        },
        record_id=artifact_id,
    )
    return _record_to_artifact(record)


def list_artifacts(
    stage: Optional[str] = None,
    base_dir: str = ".",
    project_root: Optional[str] = None,
) -> list[dict[str, Any]]:
    """List compact deliverables plus read-only legacy artifact entries."""
    root = resolve_project_root(project_root=project_root, base_dir=base_dir)
    compact = [_record_to_artifact(record) for record in list_project_records(str(root), kind="artifact")]
    combined = [*_legacy_artifacts(root), *compact]
    if stage:
        return [artifact for artifact in combined if artifact.get("stage") == stage]
    return combined


def get_artifact(
    artifact_id: str,
    base_dir: str = ".",
    project_root: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """Fetch one compact or legacy artifact without rewriting either store."""
    for artifact in list_artifacts(base_dir=base_dir, project_root=project_root):
        if artifact.get("artifact_id") == artifact_id:
            return artifact
    return None
