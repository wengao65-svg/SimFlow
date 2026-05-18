"""Optional helper-run recording utilities.

These utilities record scripts, commands, inputs, outputs, and lineage without
requiring a specific parser, plotting library, simulation engine, or report
filename.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .artifact import list_artifacts, register_artifact
from .state import ensure_workflow_initialized, resolve_project_root


HELPER_ARTIFACT_TYPE = "helper_run_manifest"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "helper_run"


def _relative_path(project_root: Path, value: str | Path) -> str:
    path = Path(value).expanduser()
    resolved = path if path.is_absolute() else project_root / path
    try:
        return str(resolved.resolve().relative_to(project_root.resolve()))
    except ValueError:
        return str(path)


def _artifact_name(value: str | Path) -> str:
    return Path(value).name or str(value)


def _register_path_artifact(
    *,
    project_root: Path,
    stage: str,
    path: str,
    artifact_type: str,
    parent_artifacts: list[str],
    role: str,
    helper_name: Optional[str],
    metadata: Optional[dict[str, Any]] = None,
    software: Optional[str] = None,
) -> dict[str, Any]:
    artifact_metadata = {
        "role": role,
        "helper_name": helper_name,
        **(metadata or {}),
    }
    return register_artifact(
        _artifact_name(path),
        artifact_type,
        stage,
        project_root=str(project_root),
        path=_relative_path(project_root, path),
        parent_artifacts=parent_artifacts,
        parameters={"helper_name": helper_name, "role": role},
        software=software,
        metadata=artifact_metadata,
    )


def record_helper_run(
    *,
    project_root: str,
    stage: str,
    run_name: str,
    command: Optional[str] = None,
    script_path: Optional[str] = None,
    input_paths: Optional[list[str]] = None,
    output_paths: Optional[list[str]] = None,
    environment: Optional[dict[str, Any]] = None,
    helper_name: Optional[str] = None,
    parent_artifacts: Optional[list[str]] = None,
    metadata: Optional[dict[str, Any]] = None,
    software: Optional[str] = None,
) -> dict[str, Any]:
    """Record an optional helper run and its artifacts.

    The helper may be an internal parser, self-written Python, a notebook,
    domain library, plotting script, shell command, or any other reasonable
    analysis/modeling/writing aid. SimFlow records what happened; it does not
    require the helper to be pre-declared.
    """
    root = resolve_project_root(project_root=project_root)
    ensure_workflow_initialized(project_root=str(root))

    run_id = f"helper_{uuid.uuid4().hex[:8]}"
    parent_ids = list(dict.fromkeys(parent_artifacts or []))
    helper = helper_name or "custom"
    input_paths = input_paths or []
    output_paths = output_paths or []
    metadata = metadata or {}

    script_artifact = None
    if script_path:
        script_artifact = _register_path_artifact(
            project_root=root,
            stage=stage,
            path=script_path,
            artifact_type="helper_script",
            parent_artifacts=parent_ids,
            role="script",
            helper_name=helper,
            metadata=metadata.get("script_metadata") if isinstance(metadata.get("script_metadata"), dict) else None,
            software=software,
        )

    input_artifacts = [
        _register_path_artifact(
            project_root=root,
            stage=stage,
            path=path,
            artifact_type="helper_input",
            parent_artifacts=parent_ids,
            role="input",
            helper_name=helper,
            metadata=metadata.get("input_metadata") if isinstance(metadata.get("input_metadata"), dict) else None,
            software=software,
        )
        for path in input_paths
    ]

    output_parent_ids = [
        *parent_ids,
        *([script_artifact["artifact_id"]] if script_artifact else []),
        *(artifact["artifact_id"] for artifact in input_artifacts),
    ]
    output_artifacts = [
        _register_path_artifact(
            project_root=root,
            stage=stage,
            path=path,
            artifact_type="helper_output",
            parent_artifacts=output_parent_ids,
            role="output",
            helper_name=helper,
            metadata=metadata.get("output_metadata") if isinstance(metadata.get("output_metadata"), dict) else None,
            software=software,
        )
        for path in output_paths
    ]

    manifest_rel = str(Path(".simflow") / "artifacts" / stage / f"{_slug(run_name)}_helper_run.json")
    manifest_path = root / manifest_rel
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "run_id": run_id,
        "run_name": run_name,
        "stage": stage,
        "helper_name": helper,
        "command": command,
        "script_path": _relative_path(root, script_path) if script_path else None,
        "input_paths": [_relative_path(root, path) for path in input_paths],
        "output_paths": [_relative_path(root, path) for path in output_paths],
        "environment": environment or {},
        "metadata": metadata,
        "parent_artifact_ids": parent_ids,
        "script_artifact_id": script_artifact["artifact_id"] if script_artifact else None,
        "input_artifact_ids": [artifact["artifact_id"] for artifact in input_artifacts],
        "output_artifact_ids": [artifact["artifact_id"] for artifact in output_artifacts],
        "created_at": _now_iso(),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    manifest_parents = [
        *output_parent_ids,
        *(artifact["artifact_id"] for artifact in output_artifacts),
    ]
    manifest_artifact = register_artifact(
        manifest_path.name,
        HELPER_ARTIFACT_TYPE,
        stage,
        project_root=str(root),
        path=manifest_rel,
        parent_artifacts=list(dict.fromkeys(manifest_parents)),
        parameters={
            "helper_name": helper,
            "command": command,
            "script_path": manifest["script_path"],
        },
        software=software,
        metadata={"helper_optional": True, **metadata},
    )

    artifacts = [
        *( [script_artifact] if script_artifact else [] ),
        *input_artifacts,
        *output_artifacts,
        manifest_artifact,
    ]
    return {
        "status": "success",
        "run_id": run_id,
        "manifest": manifest,
        "manifest_artifact": manifest_artifact,
        "artifacts": artifacts,
    }


def list_helper_runs(
    *,
    project_root: str,
    stage: Optional[str] = None,
) -> list[dict[str, Any]]:
    """List recorded optional helper-run manifest artifacts."""
    return [
        artifact
        for artifact in list_artifacts(stage=stage, project_root=project_root)
        if artifact.get("type") == HELPER_ARTIFACT_TYPE
    ]
