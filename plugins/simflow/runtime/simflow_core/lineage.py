"""Read-only lineage derived from logical artifact records."""

from __future__ import annotations

from typing import Optional

from .artifacts import list_artifacts


def _artifacts(base_dir: str = ".", project_root: Optional[str] = None) -> list[dict]:
    return list_artifacts(base_dir=base_dir, project_root=project_root)


def _links_for(artifact: dict) -> list[dict]:
    return [
        {
            "child_artifact_id": artifact["artifact_id"],
            "parent_artifact_id": parent_id,
            "relationship": "derived_from",
            "stage": artifact.get("stage"),
            "parameters": artifact.get("lineage", {}).get("parameters", {}),
        }
        for parent_id in artifact.get("lineage", {}).get("parent_artifacts", []) or []
    ]


def record_artifact_node(artifact: dict, base_dir: str = ".", project_root: Optional[str] = None) -> dict:
    """Return the derived node; compact records already contain this data."""
    del base_dir, project_root
    return {
        key: artifact.get(key)
        for key in ("artifact_id", "name", "type", "stage", "version", "path", "checksum")
    }


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
    """Return a derived link without creating a second lineage registry."""
    del base_dir, project_root
    return {
        "child_artifact_id": child_artifact_id,
        "parent_artifact_id": parent_artifact_id,
        "relationship": relationship,
        "stage": stage,
        "parameters": parameters or {},
    }


def record_artifact_lineage(
    artifact: dict,
    base_dir: str = ".",
    project_root: Optional[str] = None,
) -> dict:
    """Return lineage already embedded in one logical artifact record."""
    del base_dir, project_root
    return {"artifact_id": artifact["artifact_id"], "links": _links_for(artifact)}


def get_lineage(
    artifact_id: str,
    base_dir: str = ".",
    project_root: Optional[str] = None,
) -> Optional[dict]:
    for artifact in _artifacts(base_dir, project_root=project_root):
        if artifact.get("artifact_id") != artifact_id:
            continue
        lineage = dict(artifact.get("lineage", {}))
        lineage["links"] = _links_for(artifact)
        return lineage
    return None


def get_dependency_tree(
    artifact_id: str,
    base_dir: str = ".",
    project_root: Optional[str] = None,
) -> dict:
    artifacts = _artifacts(base_dir, project_root=project_root)
    artifact_map = {artifact.get("artifact_id"): artifact for artifact in artifacts}

    def build(current_id: str, visited: set[str]) -> dict:
        if current_id in visited or current_id not in artifact_map:
            return {"artifact_id": current_id, "parents": []}
        visited.add(current_id)
        artifact = artifact_map[current_id]
        parent_ids = artifact.get("lineage", {}).get("parent_artifacts", []) or []
        return {
            "artifact_id": current_id,
            "name": artifact.get("name"),
            "type": artifact.get("type"),
            "version": artifact.get("version"),
            "stage": artifact.get("stage"),
            "parents": [build(parent_id, visited) for parent_id in parent_ids],
        }

    return build(artifact_id, set())


def get_descendants(
    artifact_id: str,
    base_dir: str = ".",
    project_root: Optional[str] = None,
) -> list[dict]:
    return [
        artifact
        for artifact in _artifacts(base_dir, project_root=project_root)
        if artifact_id in (artifact.get("lineage", {}).get("parent_artifacts", []) or [])
    ]


def record_parameters(
    artifact_id: str,
    parameters: dict,
    base_dir: str = ".",
    project_root: Optional[str] = None,
) -> dict:
    """Reject in-place history mutation; callers should append a new record."""
    del artifact_id, parameters, base_dir, project_root
    raise RuntimeError("Artifact history is append-only; record a superseding deliverable instead")


def get_stage_lineage(
    stage: str,
    base_dir: str = ".",
    project_root: Optional[str] = None,
) -> list[dict]:
    return [
        {
            "artifact_id": artifact["artifact_id"],
            "name": artifact["name"],
            "type": artifact["type"],
            "version": artifact["version"],
            "parents": artifact.get("lineage", {}).get("parent_artifacts", []),
            "software": artifact.get("lineage", {}).get("software"),
        }
        for artifact in _artifacts(base_dir, project_root=project_root)
        if artifact.get("stage") == stage
    ]
