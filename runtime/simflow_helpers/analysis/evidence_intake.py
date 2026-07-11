"""Generic user-provided analysis/visualization evidence intake."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runtime.simflow_core.artifacts import register_artifact
from runtime.simflow_core.checkpoints import create_checkpoint
from runtime.simflow_core.proposals import load_proposal_contract
from runtime.simflow_core.readiness import build_stage_readiness
from runtime.simflow_core.state import read_state, update_stage
from runtime.simflow_core.toolchains import build_actual_tool_used, normalize_tool_name


EVIDENCE_TYPES = {
    "analysis_script": "analysis_script",
    "analysis_inputs": "analysis_inputs",
    "analysis_outputs": "analysis_outputs",
    "analysis_environment": "analysis_environment",
    "figure_files": "figure",
    "figure_manifest": "figures_manifest",
    "claim_evidence_map": "claim_evidence_map",
    "visual_qa": "visual_qa_report",
    "validation_report": "analysis_validation_report",
    "derived_data": "derived_analysis_data",
}


def resolve_project_root_from_workflow_dir(workflow_dir: str) -> Path:
    path = Path(workflow_dir).expanduser().resolve()
    return path.parent if path.name == ".simflow" else path


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_list(value: Any) -> list[Any]:
    if value in (None, "", False):
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _relative_path(project_root: Path, value: str | Path) -> str:
    path = Path(value).expanduser()
    resolved = path if path.is_absolute() else project_root / path
    try:
        return str(resolved.resolve().relative_to(project_root.resolve()))
    except ValueError:
        return str(resolved.resolve())


def _entry_paths(entry: Any) -> list[str]:
    if isinstance(entry, dict):
        paths = []
        if entry.get("path"):
            paths.append(str(entry["path"]))
        paths.extend(str(path) for path in _as_list(entry.get("paths")))
        return paths
    return [str(value) for value in _as_list(entry)]


def _entry_metadata(entry: Any) -> dict[str, Any]:
    if isinstance(entry, dict) and isinstance(entry.get("metadata"), dict):
        return dict(entry["metadata"])
    return {}


def _entry_parameters(entry: Any) -> dict[str, Any]:
    if isinstance(entry, dict) and isinstance(entry.get("parameters"), dict):
        return dict(entry["parameters"])
    return {}


def _entry_name(path: str, entry: Any) -> str:
    if isinstance(entry, dict) and entry.get("name"):
        return str(entry["name"])
    return Path(path).name or str(path)


def _collect_evidence_entries(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for evidence_key, value in evidence.items():
        normalized_key = str(evidence_key)
        artifact_type = EVIDENCE_TYPES.get(normalized_key, normalized_key)
        values = value if isinstance(value, list) else _as_list(value)
        for item in values:
            for path in _entry_paths(item):
                entries.append({
                    "evidence_key": normalized_key,
                    "artifact_type": artifact_type,
                    "path": path,
                    "name": _entry_name(path, item),
                    "metadata": _entry_metadata(item),
                    "parameters": _entry_parameters(item),
                })
    return entries


def _validate_paths(project_root: Path, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    missing = []
    for entry in entries:
        path = Path(entry["path"]).expanduser()
        resolved = path if path.is_absolute() else project_root / path
        if not resolved.exists():
            missing.append({"evidence_key": entry["evidence_key"], "path": entry["path"]})
    return missing


def _write_manifest(project_root: Path, manifest: dict[str, Any]) -> Path:
    reports_dir = project_root / ".simflow" / "reports" / "analysis"
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / "analysis_evidence_intake_manifest.json"
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def _load_contract(project_root: Path) -> dict[str, Any]:
    try:
        return load_proposal_contract(str(project_root / ".simflow"), allow_direct_entry=True)
    except Exception:
        return {}


def record_analysis_evidence(
    workflow_dir: str,
    params: dict[str, Any] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Record user-provided analysis/visualization evidence as artifacts."""
    project_root = resolve_project_root_from_workflow_dir(workflow_dir)
    state = read_state(project_root=str(project_root), state_file="workflow.json")
    if not state:
        return {"status": "error", "message": "No workflow state found"}

    params = params or {}
    evidence = params.get("evidence") or {}
    if not isinstance(evidence, dict) or not evidence:
        return {"status": "error", "message": "params.evidence must be a non-empty object"}

    contract = _load_contract(project_root)
    software = normalize_tool_name(params.get("software") or contract.get("software") or "custom")
    task = params.get("task") or contract.get("task") or contract.get("job_type") or "unknown"
    command = params.get("command")
    version = params.get("version")
    environment = params.get("environment")
    complete_stage = bool(params.get("complete_stage", False))
    parent_artifacts = [str(item) for item in _as_list(params.get("parent_artifacts"))]
    actual_tool_used = build_actual_tool_used(
        contract,
        software,
        command=command,
        version=version,
        environment=environment,
    )

    entries = _collect_evidence_entries(evidence)
    if not entries:
        return {"status": "error", "message": "No evidence paths were provided"}

    missing = _validate_paths(project_root, entries)
    if missing:
        return {"status": "error", "message": "Evidence path(s) do not exist", "missing": missing}

    manifest = {
        "generated_at": _now_iso(),
        "software": software,
        "task": task,
        "command": command,
        "version": version,
        "environment": environment or {},
        "actual_tool_used": actual_tool_used,
        "source": "user_provided_analysis_evidence",
        "complete_stage_requested": complete_stage,
        "accepted_evidence": [
            {
                "evidence_key": entry["evidence_key"],
                "artifact_type": entry["artifact_type"],
                "path": _relative_path(project_root, entry["path"]),
                "name": entry["name"],
            }
            for entry in entries
        ],
        "parent_artifact_ids": parent_artifacts,
    }

    if dry_run:
        manifest["planned_outputs"] = [".simflow/reports/analysis/analysis_evidence_intake_manifest.json"]
        return {"status": "dry_run_complete", "manifest": manifest, "planned_artifacts": manifest["accepted_evidence"]}

    artifacts = []
    for entry in entries:
        metadata = {
            "source": "user_provided",
            "evidence_keys": [entry["evidence_key"]],
            "actual_tool_used": actual_tool_used,
            **entry["metadata"],
        }
        artifacts.append(register_artifact(
            entry["name"],
            entry["artifact_type"],
            "analysis_visualization",
            project_root=str(project_root),
            path=_relative_path(project_root, entry["path"]),
            parent_artifacts=parent_artifacts,
            parameters={
                "software": software,
                "task": task,
                "command": command,
                **entry["parameters"],
            },
            software=software,
            metadata=metadata,
        ))

    manifest["artifact_ids"] = [artifact["artifact_id"] for artifact in artifacts]
    manifest_path = _write_manifest(project_root, manifest)
    manifest_artifact = register_artifact(
        "analysis_evidence_intake_manifest.json",
        "analysis_evidence_intake_manifest",
        "analysis_visualization",
        project_root=str(project_root),
        path=_relative_path(project_root, manifest_path),
        parent_artifacts=[*parent_artifacts, *manifest["artifact_ids"]],
        parameters={"software": software, "task": task, "command": command},
        software=software,
        metadata={
            "source": "user_provided_analysis_evidence",
            "evidence_keys": ["analysis_evidence_intake_manifest"],
            "actual_tool_used": actual_tool_used,
        },
    )
    artifacts.append(manifest_artifact)

    readiness = build_stage_readiness(str(project_root), stage="analysis_visualization")
    checkpoint = None
    if complete_stage and readiness["readiness_status"] == "ready":
        output_ids = [artifact["artifact_id"] for artifact in artifacts]
        update_stage(
            "analysis_visualization",
            "completed",
            project_root=str(project_root),
            inputs=parent_artifacts,
            outputs=output_ids,
        )
        checkpoint = create_checkpoint(
            state.get("workflow_id", "unknown"),
            "analysis_visualization",
            "User-provided analysis evidence intake complete",
            project_root=str(project_root),
            job_id="user_provided_analysis_evidence",
        )
        readiness = build_stage_readiness(str(project_root), stage="analysis_visualization")

    return {
        "status": "success",
        "project_root": str(project_root),
        "artifacts": artifacts,
        "manifest": manifest,
        "readiness": readiness,
        "checkpoint_id": checkpoint["checkpoint_id"] if checkpoint else None,
        "stage_completed": bool(checkpoint),
    }
