"""Artifact lineage tracking: provenance, dependencies, and parameter recording."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .artifact import _read_artifacts


def get_lineage(artifact_id: str, base_dir: str = ".") -> Optional[dict]:
    """Get the full lineage of an artifact."""
    artifacts = _read_artifacts(base_dir)
    for a in artifacts:
        if a["artifact_id"] == artifact_id:
            return a.get("lineage", {})
    return None


def get_dependency_tree(artifact_id: str, base_dir: str = ".") -> dict:
    """Build a dependency tree for an artifact (recursive parent lookup)."""
    artifacts = _read_artifacts(base_dir)
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


def get_descendants(artifact_id: str, base_dir: str = ".") -> list:
    """Find all artifacts that depend on the given artifact."""
    artifacts = _read_artifacts(base_dir)
    descendants = []
    for a in artifacts:
        lineage = a.get("lineage", {})
        parents = lineage.get("parent_artifacts", [])
        if artifact_id in parents:
            descendants.append(a)
    return descendants


def record_parameters(artifact_id: str, parameters: dict, base_dir: str = ".") -> dict:
    """Update parameters in an artifact's lineage."""
    artifacts = _read_artifacts(base_dir)
    for a in artifacts:
        if a["artifact_id"] == artifact_id:
            if "lineage" not in a:
                a["lineage"] = {}
            a["lineage"]["parameters"] = parameters
            _write_artifacts(artifacts, base_dir)
            return a
    raise ValueError(f"Artifact not found: {artifact_id}")


def get_stage_lineage(stage: str, base_dir: str = ".") -> list:
    """Get lineage info for all artifacts produced in a stage."""
    artifacts = _read_artifacts(base_dir)
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


def _write_artifacts(artifacts: list, base_dir: str = ".") -> None:
    """Write artifacts registry back to disk."""
    path = Path(base_dir) / ".simflow" / "state" / "artifacts.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(artifacts, f, indent=2, ensure_ascii=False)
