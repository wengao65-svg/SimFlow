#!/usr/bin/env python3
"""Generate final handoff deliverables for Milestone D."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(ROOT))

from generate_handoff import generate_handoff, resolve_project_root_from_workflow_dir
from runtime.lib.artifact import register_artifact
from runtime.lib.state import read_state

SENSITIVE_KEY_PARTS = ("password", "token", "secret", "credential", "api_key", "apikey")


def _relative_path(project_root: Path, path: Path) -> str:
    return str(path.resolve().relative_to(project_root))


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(part in lowered for part in SENSITIVE_KEY_PARTS)


def _is_absolute_path_string(value: str) -> bool:
    if not value:
        return False
    if Path(value).is_absolute():
        return True
    windows_path = PureWindowsPath(value)
    return windows_path.is_absolute() or value.startswith("\\")


def _sanitize_path(value: str, project_root: Path) -> str:
    try:
        resolved = Path(value).expanduser().resolve()
        return str(resolved.relative_to(project_root.resolve()))
    except Exception:
        parts = [part for part in re.split(r"[\\/]+", value) if part]
        return parts[-1] if parts else "<sanitized_path>"


def _sanitize_value(value: Any, project_root: Path) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            if _is_sensitive_key(key):
                sanitized[key] = "<redacted>"
                continue
            sanitized[key] = _sanitize_value(item, project_root)
        return sanitized

    if isinstance(value, list):
        return [_sanitize_value(item, project_root) for item in value]

    if isinstance(value, str) and _is_absolute_path_string(value):
        return _sanitize_path(value, project_root)

    return value


def _latest_artifact(
    artifacts: list[dict[str, Any]],
    *,
    name: str | None = None,
    artifact_type: str | None = None,
    stage: str | None = None,
) -> dict[str, Any] | None:
    matches = [
        artifact
        for artifact in artifacts
        if (name is None or artifact.get("name") == name)
        and (artifact_type is None or artifact.get("type") == artifact_type)
        and (stage is None or artifact.get("stage") == stage)
    ]
    return matches[-1] if matches else None


def _artifact_reference(artifact: dict[str, Any] | None, project_root: Path) -> dict[str, Any] | None:
    if artifact is None:
        return None
    return _sanitize_value(
        {
            "artifact_id": artifact.get("artifact_id"),
            "name": artifact.get("name"),
            "type": artifact.get("type"),
            "stage": artifact.get("stage"),
            "path": artifact.get("path"),
            "version": artifact.get("version"),
        },
        project_root,
    )


def _read_artifact_json(project_root: Path, artifact: dict[str, Any] | None) -> dict[str, Any]:
    if artifact is None:
        return {}
    path_value = artifact.get("path")
    if not path_value:
        return {}
    path = project_root / path_value
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _derive_source_artifact_ids(
    artifacts: list[dict[str, Any]],
    explicit_source_artifact_ids: list[str] | None,
) -> list[str]:
    if explicit_source_artifact_ids:
        return list(dict.fromkeys(explicit_source_artifact_ids))

    writing_artifact_ids = {
        artifact.get("artifact_id")
        for artifact in artifacts
        if artifact.get("stage") == "writing"
    }
    candidate_ids: list[str] = []
    reproducibility_package_artifact = _latest_artifact(artifacts, name="reproducibility_package.md", stage="writing")
    if reproducibility_package_artifact is not None:
        candidate_ids.extend(reproducibility_package_artifact.get("lineage", {}).get("parent_artifacts", []))
    else:
        for artifact_name in ("methods.md", "results.md", "reproducibility_manifest.json"):
            artifact = _latest_artifact(artifacts, name=artifact_name, stage="writing")
            if artifact is not None:
                candidate_ids.extend(artifact.get("lineage", {}).get("parent_artifacts", []))

    source_artifact_ids = []
    seen: set[str] = set()
    for artifact_id in candidate_ids:
        if not artifact_id or artifact_id in writing_artifact_ids or artifact_id in seen:
            continue
        seen.add(artifact_id)
        source_artifact_ids.append(artifact_id)
    return source_artifact_ids


def _artifact_summary(artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    by_stage: dict[str, int] = {}
    by_type: dict[str, int] = {}
    for artifact in artifacts:
        stage = artifact.get("stage", "unknown")
        artifact_type = artifact.get("type", "unknown")
        by_stage[stage] = by_stage.get(stage, 0) + 1
        by_type[artifact_type] = by_type.get(artifact_type, 0) + 1
    return {
        "artifacts_count": len(artifacts),
        "artifacts_by_stage": by_stage,
        "artifacts_by_type": by_type,
    }


def _planned_final_output_reference(project_root: Path, name: str, artifact_type: str) -> dict[str, Any]:
    path = project_root / ".simflow" / "reports" / "handoff" / name
    return {
        "name": name,
        "type": artifact_type,
        "stage": "writing",
        "path": _relative_path(project_root, path),
    }


def _format_reference(reference: dict[str, Any] | None) -> str:
    if not reference:
        return "N/A"
    artifact_id = reference.get("artifact_id")
    path = reference.get("path") or reference.get("name") or "N/A"
    if artifact_id:
        return f"{artifact_id} ({path})"
    return path


def _summarize_warnings(warnings: list[dict[str, Any]]) -> list[str]:
    summary = []
    for warning in warnings:
        warning_type = warning.get("type", "warning")
        field = warning.get("field", "unknown")
        replacement = warning.get("replacement")
        if replacement:
            summary.append(f"{warning_type}: {field} -> {replacement}")
        else:
            summary.append(f"{warning_type}: {field}")
    return summary


def build_final_handoff_data(
    workflow_dir: str,
    source_artifact_ids: list[str] | None = None,
) -> dict[str, Any]:
    project_root = resolve_project_root_from_workflow_dir(workflow_dir)
    handoff_result = generate_handoff(workflow_dir)
    if handoff_result.get("status") != "success":
        return handoff_result

    workflow = read_state(project_root=str(project_root), state_file="workflow.json")
    metadata = read_state(project_root=str(project_root), state_file="metadata.json")
    artifacts_state = read_state(project_root=str(project_root), state_file="artifacts.json")
    artifacts = artifacts_state if isinstance(artifacts_state, list) else []
    handoff = handoff_result["handoff"]

    reproducibility_manifest_artifact = _latest_artifact(artifacts, name="reproducibility_manifest.json", stage="writing")
    reproducibility_manifest = _read_artifact_json(project_root, reproducibility_manifest_artifact)
    writing_refs = reproducibility_manifest.get("writing_artifact_references", {})
    writing_artifacts = [artifact for artifact in artifacts if artifact.get("stage") == "writing"]

    def writing_reference(name: str, field: str) -> dict[str, Any] | None:
        return writing_refs.get(field) or _artifact_reference(
            _latest_artifact(writing_artifacts, name=name, stage="writing"),
            project_root,
        )

    compute_truth = reproducibility_manifest.get(
        "execution_truth",
        {
            "dry_run": True,
            "real_submit": False,
            "approval_required_for_real_submit": True,
        },
    )

    final_stage = "writing"
    completed_stages = list(dict.fromkeys([*handoff.get("completed_stages", []), final_stage]))
    pending_stages = [stage for stage in handoff.get("pending_stages", []) if stage != final_stage]
    failed_stages = handoff.get("failed_stages", [])
    workflow_status = "completed" if not pending_stages and not failed_stages else workflow.get("status", "unknown")

    resolved_source_artifact_ids = _derive_source_artifact_ids(artifacts, source_artifact_ids)
    planned_final_markdown = _planned_final_output_reference(project_root, "final_handoff.md", "final_handoff")
    planned_final_json = _planned_final_output_reference(project_root, "final_handoff.json", "final_handoff_summary")

    risks = list(handoff.get("risks", []))
    unresolved_items: list[str] = []
    if not compute_truth.get("real_submit", False):
        message = "No real HPC submit was executed; deliverables summarize dry-run or waiting-state evidence."
        risks.append(message)
        unresolved_items.append(message)
    if reproducibility_manifest.get("figure_provenance", {}).get("status") not in {None, "completed"}:
        unresolved_items.append(
            "Figure provenance is incomplete or degraded: "
            f"{reproducibility_manifest.get('figure_provenance', {}).get('status', 'unknown')}."
        )
    if failed_stages:
        unresolved_items.append(f"Failed stages: {', '.join(failed_stages)}")
    if pending_stages:
        unresolved_items.append(f"Pending stages: {', '.join(pending_stages)}")
    warning_summary = _summarize_warnings(reproducibility_manifest.get("warnings", []))
    if warning_summary:
        unresolved_items.append(f"Manifest warnings: {len(warning_summary)} item(s).")

    next_steps = []
    if workflow_status == "completed":
        next_steps.append("Workflow complete")
        next_steps.append("Review final deliverables and decide whether additional compute or publication packaging is needed.")
    else:
        next_steps.extend(handoff.get("next_steps", []))

    workflow_metadata = reproducibility_manifest.get(
        "workflow_metadata",
        {
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
        },
    )
    workflow_metadata = {
        **workflow_metadata,
        "current_stage": final_stage,
        "status": workflow_status,
    }

    final_handoff = {
        "workflow_metadata": workflow_metadata,
        "current_stage": final_stage,
        "completed_stages": completed_stages,
        "pending_stages": pending_stages,
        "failed_stages": failed_stages,
        "latest_checkpoint": handoff.get("latest_checkpoint") or reproducibility_manifest.get("checkpoint_summary", {}).get("latest"),
        "artifact_summary": _artifact_summary(artifacts),
        "writing_outputs": {
            "methods": writing_reference("methods.md", "methods"),
            "results": writing_reference("results.md", "results"),
            "final_handoff_markdown": planned_final_markdown,
            "final_handoff_json": planned_final_json,
        },
        "reproducibility_outputs": {
            "reproducibility_package": writing_reference("reproducibility_package.md", "reproducibility_package"),
            "reproducibility_manifest": writing_reference("reproducibility_manifest.json", "reproducibility_manifest"),
        },
        "compute_truth": {
            "dry_run": bool(compute_truth.get("dry_run", True)),
            "real_submit": bool(compute_truth.get("real_submit", False)),
            "approval_required_for_real_submit": bool(compute_truth.get("approval_required_for_real_submit", True)),
        },
        "risks": list(dict.fromkeys(risks)),
        "unresolved_items": list(dict.fromkeys(unresolved_items)),
        "next_steps": list(dict.fromkeys(next_steps)),
        "source_artifact_ids": resolved_source_artifact_ids,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    final_handoff = _sanitize_value(final_handoff, project_root)
    return {"status": "success", "final_handoff": final_handoff}


def _build_final_handoff_markdown(final_handoff: dict[str, Any]) -> str:
    workflow_metadata = final_handoff["workflow_metadata"]
    writing_outputs = final_handoff["writing_outputs"]
    reproducibility_outputs = final_handoff["reproducibility_outputs"]
    compute_truth = final_handoff["compute_truth"]
    latest_checkpoint = final_handoff.get("latest_checkpoint") or {}

    def bullet_list(items: list[str], empty: str = "- None") -> str:
        return "\n".join(f"- {item}" for item in items) if items else empty

    deliverables = [
        f"Methods: {_format_reference(writing_outputs.get('methods'))}",
        f"Results: {_format_reference(writing_outputs.get('results'))}",
        f"Reproducibility package: {_format_reference(reproducibility_outputs.get('reproducibility_package'))}",
        f"Final handoff markdown: {_format_reference(writing_outputs.get('final_handoff_markdown'))}",
        f"Final handoff JSON: {_format_reference(writing_outputs.get('final_handoff_json'))}",
    ]

    return "\n".join([
        "# Final Handoff",
        "",
        "## Workflow summary",
        "",
        f"- Workflow ID: {workflow_metadata.get('workflow_id', 'unknown')}",
        f"- Workflow type: {workflow_metadata.get('workflow_type', 'unknown')}",
        f"- Current stage: {final_handoff.get('current_stage', 'unknown')}",
        f"- Workflow status: {workflow_metadata.get('status', 'unknown')}",
        f"- Research goal: {workflow_metadata.get('research_goal', 'N/A')}",
        f"- Material: {workflow_metadata.get('material', 'N/A')}",
        f"- Software: {workflow_metadata.get('software', 'N/A')}",
        f"- Latest checkpoint: {latest_checkpoint.get('checkpoint_id', 'N/A')} ({latest_checkpoint.get('stage_id', 'unknown')})",
        "",
        "## Completed stages",
        "",
        bullet_list(final_handoff.get("completed_stages", [])),
        "",
        "## Key deliverables",
        "",
        bullet_list(deliverables),
        "",
        "## Writing outputs",
        "",
        bullet_list([
            f"Methods: {_format_reference(writing_outputs.get('methods'))}",
            f"Results: {_format_reference(writing_outputs.get('results'))}",
            f"Final handoff markdown: {_format_reference(writing_outputs.get('final_handoff_markdown'))}",
            f"Final handoff JSON: {_format_reference(writing_outputs.get('final_handoff_json'))}",
        ]),
        "",
        "## Reproducibility package",
        "",
        bullet_list([
            f"Package: {_format_reference(reproducibility_outputs.get('reproducibility_package'))}",
            f"Manifest: {_format_reference(reproducibility_outputs.get('reproducibility_manifest'))}",
        ]),
        "",
        "## Compute truth / real submit status",
        "",
        bullet_list([
            f"Dry-run: {compute_truth.get('dry_run', True)}",
            f"Real submit: {compute_truth.get('real_submit', False)}",
            f"Approval required for real submit: {compute_truth.get('approval_required_for_real_submit', True)}",
        ]),
        "",
        "## Risks and unresolved items",
        "",
        bullet_list(final_handoff.get("risks", []) + final_handoff.get("unresolved_items", [])),
        "",
        "## Next steps",
        "",
        bullet_list(final_handoff.get("next_steps", [])),
        "",
        "## Source artifact traceability",
        "",
        bullet_list(final_handoff.get("source_artifact_ids", [])),
    ])


def generate_final_handoff(
    workflow_dir: str,
    source_artifact_ids: list[str] | None = None,
    parent_artifact_ids: list[str] | None = None,
    software: str | None = None,
) -> dict[str, Any]:
    project_root = resolve_project_root_from_workflow_dir(workflow_dir)
    reports_dir = project_root / ".simflow" / "reports" / "handoff"
    reports_dir.mkdir(parents=True, exist_ok=True)
    final_markdown_path = reports_dir / "final_handoff.md"
    final_json_path = reports_dir / "final_handoff.json"

    build_result = build_final_handoff_data(workflow_dir, source_artifact_ids=source_artifact_ids)
    if build_result.get("status") != "success":
        return build_result

    final_handoff = build_result["final_handoff"]
    final_json_path.write_text(json.dumps(final_handoff, indent=2, ensure_ascii=False), encoding="utf-8")
    final_markdown_path.write_text(_build_final_handoff_markdown(final_handoff), encoding="utf-8")

    lineage_parent_artifacts = list(dict.fromkeys(parent_artifact_ids or source_artifact_ids or final_handoff.get("source_artifact_ids", [])))
    final_json_artifact = register_artifact(
        "final_handoff.json",
        "final_handoff_summary",
        "writing",
        project_root=str(project_root),
        path=_relative_path(project_root, final_json_path),
        parent_artifacts=lineage_parent_artifacts,
        parameters={"software": software, "output": "json"},
        software=software,
    )
    final_markdown_artifact = register_artifact(
        "final_handoff.md",
        "final_handoff",
        "writing",
        project_root=str(project_root),
        path=_relative_path(project_root, final_markdown_path),
        parent_artifacts=[final_json_artifact["artifact_id"], *lineage_parent_artifacts],
        parameters={"software": software, "output": "markdown"},
        software=software,
    )

    return {
        "status": "success",
        "artifacts": [final_markdown_artifact, final_json_artifact],
        "final_handoff": final_handoff,
        "outputs": [
            _relative_path(project_root, final_markdown_path),
            _relative_path(project_root, final_json_path),
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate final handoff deliverables")
    parser.add_argument("--workflow-dir", required=True, help="Path to .simflow directory")
    parser.add_argument("--source-artifact-ids", default="[]", help="JSON list of upstream source artifact IDs")
    parser.add_argument("--parent-artifact-ids", default="[]", help="JSON list of lineage parent artifact IDs")
    parser.add_argument("--software", help="Software name for artifact metadata")
    args = parser.parse_args()

    try:
        source_artifact_ids = json.loads(args.source_artifact_ids)
        parent_artifact_ids = json.loads(args.parent_artifact_ids)
        result = generate_final_handoff(
            args.workflow_dir,
            source_artifact_ids=source_artifact_ids,
            parent_artifact_ids=parent_artifact_ids,
            software=args.software,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
