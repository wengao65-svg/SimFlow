"""Artifact lineage tracking: provenance, dependencies, and parameter recording."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .artifacts import _read_artifacts
from .state import ensure_workflow_initialized, resolve_project_root


LINEAGE_STATE_FILE = ".simflow/state/lineage.json"


def _empty_lineage_state() -> dict:
    return {"artifacts": [], "links": []}


def _read_lineage_state(base_dir: str = ".", project_root: Optional[str] = None) -> dict:
    """Read first-class lineage state."""
    root = resolve_project_root(project_root=project_root, base_dir=base_dir)
    path = root / LINEAGE_STATE_FILE
    if not path.exists():
        return _empty_lineage_state()
    with open(path, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    if isinstance(loaded, list):
        return {"artifacts": [], "links": loaded}
    if isinstance(loaded, dict):
        loaded.setdefault("artifacts", [])
        loaded.setdefault("links", [])
        return loaded
    return _empty_lineage_state()


def _write_lineage_state(state: dict, base_dir: str = ".", project_root: Optional[str] = None) -> None:
    """Write first-class lineage state."""
    root = resolve_project_root(project_root=project_root, base_dir=base_dir)
    ensure_workflow_initialized(project_root=str(root))
    path = root / LINEAGE_STATE_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def record_artifact_node(
    artifact: dict,
    base_dir: str = ".",
    project_root: Optional[str] = None,
) -> dict:
    """Record or update an artifact node in first-class lineage state."""
    state = _read_lineage_state(base_dir, project_root=project_root)
    nodes = state.setdefault("artifacts", [])
    node = {
        "artifact_id": artifact["artifact_id"],
        "name": artifact.get("name"),
        "type": artifact.get("type"),
        "stage": artifact.get("stage"),
        "version": artifact.get("version"),
        "path": artifact.get("path"),
        "checksum": artifact.get("checksum"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    existing_index = next((idx for idx, item in enumerate(nodes) if item.get("artifact_id") == artifact["artifact_id"]), None)
    if existing_index is None:
        nodes.append(node)
    else:
        nodes[existing_index] = node
    _write_lineage_state(state, base_dir, project_root=project_root)
    return node


def record_lineage_link(
    child_artifact_id: str,
    parent_artifact_id: str,
    *,
    relationship: str = "derived_from",
    stage: Optional[str] = None,
    parameters: Optional[dict] = None,
    base_dir: str = ".",
    project_root: Optional[str] = None,
) -> dict:
    """Record a parent-child artifact lineage link."""
    import uuid

    state = _read_lineage_state(base_dir, project_root=project_root)
    links = state.setdefault("links", [])
    existing = next(
        (
            link for link in links
            if link.get("child_artifact_id") == child_artifact_id
            and link.get("parent_artifact_id") == parent_artifact_id
            and link.get("relationship") == relationship
        ),
        None,
    )
    if existing:
        return existing

    link = {
        "link_id": f"lin_{uuid.uuid4().hex[:8]}",
        "child_artifact_id": child_artifact_id,
        "parent_artifact_id": parent_artifact_id,
        "relationship": relationship,
        "stage": stage,
        "parameters": parameters or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    links.append(link)
    _write_lineage_state(state, base_dir, project_root=project_root)
    return link


def record_artifact_lineage(
    artifact: dict,
    base_dir: str = ".",
    project_root: Optional[str] = None,
) -> dict:
    """Record an artifact node and all embedded parent links."""
    record_artifact_node(artifact, base_dir, project_root=project_root)
    lineage = artifact.get("lineage", {})
    links = []
    for parent_id in lineage.get("parent_artifacts", []) or []:
        links.append(record_lineage_link(
            child_artifact_id=artifact["artifact_id"],
            parent_artifact_id=parent_id,
            stage=artifact.get("stage"),
            parameters=lineage.get("parameters", {}),
            base_dir=base_dir,
            project_root=project_root,
        ))
    return {"artifact_id": artifact["artifact_id"], "links": links}


def get_lineage(artifact_id: str, base_dir: str = ".", project_root: Optional[str] = None) -> Optional[dict]:
    """Get the full lineage of an artifact."""
    artifacts = _read_artifacts(base_dir, project_root=project_root)
    state = _read_lineage_state(base_dir, project_root=project_root)
    for a in artifacts:
        if a["artifact_id"] == artifact_id:
            lineage = dict(a.get("lineage", {}))
            lineage["links"] = [
                link for link in state.get("links", [])
                if link.get("child_artifact_id") == artifact_id
            ]
            return lineage
    return None


def get_dependency_tree(artifact_id: str, base_dir: str = ".", project_root: Optional[str] = None) -> dict:
    """Build a dependency tree for an artifact (recursive parent lookup)."""
    artifacts = _read_artifacts(base_dir, project_root=project_root)
    art_map = {a["artifact_id"]: a for a in artifacts}

    def _build_tree(aid: str, visited: set) -> dict:
        if aid in visited or aid not in art_map:
            return {"artifact_id": aid, "parents": []}
        visited.add(aid)
        art = art_map[aid]
        lineage = art.get("lineage", {})
        parent_ids = lineage.get("parent_artifacts", [])
        parents = [_build_tree(pid, visited) for pid in parent_ids]
        return {
            "artifact_id": aid,
            "name": art.get("name"),
            "type": art.get("type"),
            "version": art.get("version"),
            "stage": art.get("stage"),
            "parents": parents,
        }

    return _build_tree(artifact_id, set())


def get_descendants(artifact_id: str, base_dir: str = ".", project_root: Optional[str] = None) -> list:
    """Find all artifacts that depend on the given artifact."""
    artifacts = _read_artifacts(base_dir, project_root=project_root)
    descendants = []
    for a in artifacts:
        lineage = a.get("lineage", {})
        parents = lineage.get("parent_artifacts", [])
        if artifact_id in parents:
            descendants.append(a)
    return descendants


def record_parameters(artifact_id: str, parameters: dict, base_dir: str = ".", project_root: Optional[str] = None) -> dict:
    """Update parameters in an artifact's lineage."""
    artifacts = _read_artifacts(base_dir, project_root=project_root)
    for a in artifacts:
        if a["artifact_id"] == artifact_id:
            if "lineage" not in a:
                a["lineage"] = {}
            a["lineage"]["parameters"] = parameters
            _write_artifacts(artifacts, base_dir, project_root=project_root)
            record_artifact_lineage(a, base_dir, project_root=project_root)
            return a
    raise ValueError(f"Artifact not found: {artifact_id}")


def get_stage_lineage(stage: str, base_dir: str = ".", project_root: Optional[str] = None) -> list:
    """Get lineage info for all artifacts produced in a stage."""
    artifacts = _read_artifacts(base_dir, project_root=project_root)
    stage_arts = [a for a in artifacts if a.get("stage") == stage]
    return [
        {
            "artifact_id": a["artifact_id"],
            "name": a["name"],
            "type": a["type"],
            "version": a["version"],
            "parents": a.get("lineage", {}).get("parent_artifacts", []),
            "software": a.get("lineage", {}).get("software"),
        }
        for a in stage_arts
    ]


def _write_artifacts(artifacts: list, base_dir: str = ".", project_root: Optional[str] = None) -> None:
    """Write artifacts registry back to disk."""
    root = resolve_project_root(project_root=project_root, base_dir=base_dir)
    ensure_workflow_initialized(project_root=str(root))
    path = root / ".simflow" / "state" / "artifacts.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(artifacts, f, indent=2, ensure_ascii=False)
