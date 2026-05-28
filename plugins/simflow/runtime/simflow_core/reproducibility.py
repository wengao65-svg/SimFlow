"""Helpers for building sanitized reproducibility manifests from canonical registries."""

from __future__ import annotations

import json
import re
from pathlib import Path, PureWindowsPath
from typing import Any, Optional

from .state import read_state, resolve_project_root

SENSITIVE_KEY_PARTS = ("password", "token", "secret", "credential", "api_key", "apikey")


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(part in lowered for part in SENSITIVE_KEY_PARTS)


def _is_absolute_path_string(value: str) -> bool:
    if not value:
        return False
    if Path(value).is_absolute():
        return True
    windows_path = PureWindowsPath(value)
    return windows_path.is_absolute() or value.startswith("\\\\")


def _sanitize_path(value: str, project_root: Path) -> str:
    try:
        resolved = Path(value).expanduser().resolve()
        return str(resolved.relative_to(project_root.resolve()))
    except Exception:
        parts = [part for part in re.split(r"[\\/]+", value) if part]
        return parts[-1] if parts else "<sanitized_path>"


def _sanitize_value(value: Any, project_root: Path, warnings: list[dict[str, Any]], field_path: str) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            child_path = f"{field_path}.{key}" if field_path else key
            if _is_sensitive_key(key):
                warnings.append({"type": "redacted_secret", "field": child_path})
                sanitized[key] = "<redacted>"
                continue
            sanitized[key] = _sanitize_value(item, project_root, warnings, child_path)
        return sanitized

    if isinstance(value, list):
        return [
            _sanitize_value(item, project_root, warnings, f"{field_path}[{index}]")
            for index, item in enumerate(value)
        ]

    if isinstance(value, str) and _is_absolute_path_string(value):
        replacement = _sanitize_path(value, project_root)
        warnings.append({
            "type": "sanitized_path",
            "field": field_path,
            "replacement": replacement,
        })
        return replacement

    return value


def _ordered_stage_names(metadata: dict[str, Any], stages: dict[str, Any]) -> list[str]:
    ordered = metadata.get("stages", []) if isinstance(metadata, dict) else []
    names = [stage for stage in ordered if isinstance(stage, str)]
    for stage_name in stages:
        if stage_name not in names:
            names.append(stage_name)
    return names


def _artifact_reference(artifact: dict[str, Any] | None, project_root: Path, warnings: list[dict[str, Any]], field_path: str) -> dict[str, Any] | None:
    if artifact is None:
        return None
    reference = {
        "artifact_id": artifact.get("artifact_id"),
        "name": artifact.get("name"),
        "type": artifact.get("type"),
        "stage": artifact.get("stage"),
        "path": artifact.get("path"),
        "version": artifact.get("version"),
    }
    return _sanitize_value(reference, project_root, warnings, field_path)


def _latest_artifact(artifacts: list[dict[str, Any]], *, name: str | None = None, artifact_type: str | None = None) -> dict[str, Any] | None:
    matches = [
        artifact
        for artifact in artifacts
        if (name is None or artifact.get("name") == name)
        and (artifact_type is None or artifact.get("type") == artifact_type)
    ]
    return matches[-1] if matches else None


def _read_artifact_json(
    project_root: Path,
    artifact: dict[str, Any] | None,
    warnings: list[dict[str, Any]],
    label: str,
) -> dict[str, Any]:
    if artifact is None:
        warnings.append({"type": "missing_artifact", "field": label})
        return {}

    path_value = artifact.get("path")
    if not path_value:
        warnings.append({"type": "missing_artifact_path", "field": label, "artifact_id": artifact.get("artifact_id")})
        return {}

    path = project_root / path_value
    if not path.is_file():
        warnings.append({"type": "missing_artifact_file", "field": label, "artifact_id": artifact.get("artifact_id")})
        return {}

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        warnings.append({"type": "invalid_json_artifact", "field": label, "artifact_id": artifact.get("artifact_id")})
        return {}


def _build_artifact_index(project_root: Path, artifacts: list[dict[str, Any]], warnings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    index = []
    for idx, artifact in enumerate(artifacts):
        entry = {
            "artifact_id": artifact.get("artifact_id"),
            "name": artifact.get("name"),
            "type": artifact.get("type"),
            "stage": artifact.get("stage"),
            "path": artifact.get("path"),
            "version": artifact.get("version"),
            "checksum": artifact.get("checksum"),
            "created_at": artifact.get("created_at"),
            "lineage": artifact.get("lineage", {}),
        }
        index.append(_sanitize_value(entry, project_root, warnings, f"artifact_index[{idx}]"))
    return index


def _build_checkpoint_summary(project_root: Path, checkpoints: list[dict[str, Any]], warnings: list[dict[str, Any]]) -> dict[str, Any]:
    latest = checkpoints[-1] if checkpoints else None
    summary = {
        "count": len(checkpoints),
        "stage_ids": [checkpoint.get("stage_id") for checkpoint in checkpoints],
        "latest": _artifact_reference(latest, project_root, warnings, "checkpoint_summary.latest") if latest else None,
    }
    if latest is not None:
        summary["latest"] = _sanitize_value(latest, project_root, warnings, "checkpoint_summary.latest")
    return summary


def _build_execution_truth(
    project_root: Path,
    artifacts: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> dict[str, Any]:
    compute_plan_artifact = _latest_artifact(artifacts, artifact_type="compute_plan")
    compute_plan = _read_artifact_json(project_root, compute_plan_artifact, warnings, "execution_truth.compute_plan")
    truth = {
        "compute_plan_artifact": _artifact_reference(compute_plan_artifact, project_root, warnings, "execution_truth.compute_plan_artifact"),
        "dry_run": bool(compute_plan.get("dry_run", True)),
        "real_submit": bool(compute_plan.get("real_submit", False)),
        "approval_required": bool(compute_plan.get("approval_required_for_real_submit", True)),
        "approval_required_for_real_submit": bool(compute_plan.get("approval_required_for_real_submit", True)),
        "approval_gate_status": _sanitize_value(
            compute_plan.get("gate_status"),
            project_root,
            warnings,
            "execution_truth.approval_gate_status",
        ),
    }
    return truth


def _build_figure_provenance(
    project_root: Path,
    artifacts: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> dict[str, Any]:
    manifest_artifact = _latest_artifact(artifacts, artifact_type="figures_manifest")
    manifest_data = _read_artifact_json(project_root, manifest_artifact, warnings, "figure_provenance.figures_manifest")
    figure_artifacts = [artifact for artifact in artifacts if artifact.get("type") == "figure"]
    figures = []
    for index, figure in enumerate(manifest_data.get("figures", [])):
        figure_artifact = _latest_artifact(figure_artifacts, name=figure.get("name"))
        figures.append(_sanitize_value({
            "name": figure.get("name"),
            "title": figure.get("title"),
            "path": figure.get("path"),
            "artifact_id": figure_artifact.get("artifact_id") if figure_artifact else None,
        }, project_root, warnings, f"figure_provenance.figures[{index}]"))

    return {
        "figures_manifest_artifact": _artifact_reference(manifest_artifact, project_root, warnings, "figure_provenance.figures_manifest_artifact"),
        "status": manifest_data.get("status"),
        "figure_count": len(figures),
        "figures": figures,
        "skipped_reasons": _sanitize_value(
            manifest_data.get("skipped_reasons", []),
            project_root,
            warnings,
            "figure_provenance.skipped_reasons",
        ),
    }


def _build_writing_artifact_references(
    project_root: Path,
    artifacts: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
    planned_outputs: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    writing_artifacts = [artifact for artifact in artifacts if artifact.get("stage") == "writing"]
    references = {
        "methods": _artifact_reference(
            _latest_artifact(writing_artifacts, name="methods.md"),
            project_root,
            warnings,
            "writing_artifact_references.methods",
        ),
        "results": _artifact_reference(
            _latest_artifact(writing_artifacts, name="results.md"),
            project_root,
            warnings,
            "writing_artifact_references.results",
        ),
        "reproducibility_package": _artifact_reference(
            _latest_artifact(writing_artifacts, name="reproducibility_package.md"),
            project_root,
            warnings,
            "writing_artifact_references.reproducibility_package",
        ),
        "reproducibility_manifest": _artifact_reference(
            _latest_artifact(writing_artifacts, name="reproducibility_manifest.json"),
            project_root,
            warnings,
            "writing_artifact_references.reproducibility_manifest",
        ),
        "planned_outputs": _sanitize_value(planned_outputs or {}, project_root, warnings, "writing_artifact_references.planned_outputs"),
    }
    return references


def build_reproducibility_manifest(
    base_dir: str = ".",
    project_root: Optional[str] = None,
    planned_outputs: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    root = resolve_project_root(project_root=project_root, base_dir=base_dir)
    workflow = read_state(project_root=str(root), state_file="workflow.json")
    metadata = read_state(project_root=str(root), state_file="metadata.json")
    artifacts_state = read_state(project_root=str(root), state_file="artifacts.json")
    checkpoints_state = read_state(project_root=str(root), state_file="checkpoints.json")
    stages_state = read_state(project_root=str(root), state_file="stages.json")

    artifacts = artifacts_state if isinstance(artifacts_state, list) else []
    checkpoints = checkpoints_state if isinstance(checkpoints_state, list) else []
    stages = stages_state if isinstance(stages_state, dict) else {}
    warnings: list[dict[str, Any]] = []

    stage_names = _ordered_stage_names(metadata if isinstance(metadata, dict) else {}, stages)
    completed = [stage for stage in stage_names if stages.get(stage, {}).get("status") == "completed"]
    pending = [stage for stage in stage_names if stages.get(stage, {}).get("status", "pending") == "pending"]
    in_progress = [stage for stage in stage_names if stages.get(stage, {}).get("status") == "in_progress"]
    failed = [stage for stage in stage_names if stages.get(stage, {}).get("status") == "failed"]

    workflow_metadata = _sanitize_value({
        "workflow_id": workflow.get("workflow_id") or metadata.get("workflow_id"),
        "workflow_type": metadata.get("workflow_type", workflow.get("workflow_type", "unknown")),
        "status": workflow.get("status", "unknown"),
        "current_stage": workflow.get("current_stage", metadata.get("current_stage", "unknown")),
        "entry_point": metadata.get("entry_point", workflow.get("entry_point")),
        "plan_reference": workflow.get("plan"),
        "research_goal": metadata.get("research_goal"),
        "material": metadata.get("material"),
        "software": metadata.get("software"),
        "created_at": workflow.get("created_at"),
        "updated_at": workflow.get("updated_at"),
    }, root, warnings, "workflow_metadata")

    artifact_index = _build_artifact_index(root, artifacts, warnings)
    checkpoint_summary = _build_checkpoint_summary(root, checkpoints, warnings)
    execution_truth = _build_execution_truth(root, artifacts, warnings)
    figure_provenance = _build_figure_provenance(root, artifacts, warnings)
    writing_artifact_references = _build_writing_artifact_references(root, artifacts, warnings, planned_outputs=planned_outputs)

    manifest = {
        "workflow_metadata": workflow_metadata,
        "completed_stages": completed,
        "pending_stages": pending,
        "in_progress_stages": in_progress,
        "failed_stages": failed,
        "artifact_index": artifact_index,
        "checkpoint_summary": checkpoint_summary,
        "execution_truth": execution_truth,
        "figure_provenance": figure_provenance,
        "writing_artifact_references": writing_artifact_references,
        "warnings": warnings,
    }
    return manifest
