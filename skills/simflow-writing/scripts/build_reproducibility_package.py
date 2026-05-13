#!/usr/bin/env python3
"""Build reproducibility package outputs for the canonical writing stage."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from runtime.lib.artifact import register_artifact
from runtime.lib.reproducibility import build_reproducibility_manifest

TEMPLATE_PATH = ROOT / "templates" / "reports" / "reproducibility_package.md.template"


def resolve_project_root_from_workflow_dir(workflow_dir: str) -> Path:
    path = Path(workflow_dir).expanduser().resolve()
    return path.parent if path.name == ".simflow" else path


def _relative_path(project_root: Path, path: Path) -> str:
    return str(path.resolve().relative_to(project_root))


def _render_template(template_content: str, variables: dict[str, Any]) -> str:
    rendered = template_content
    for key, value in variables.items():
        rendered = rendered.replace(f"{{{{ {key} }}}}", str(value))
    return rendered


def _reference_by_name(artifact_index: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    matches = [artifact for artifact in artifact_index if artifact.get("name") == name]
    return matches[-1] if matches else None


def _format_reference(reference: dict[str, Any] | None) -> str:
    if not reference:
        return "N/A"
    artifact_id = reference.get("artifact_id") or "unknown"
    path = reference.get("path") or reference.get("name") or "unknown"
    return f"{artifact_id} ({path})"


def _artifact_rows(artifact_index: list[dict[str, Any]]) -> str:
    if not artifact_index:
        return "| N/A | N/A | N/A | N/A | N/A |"
    rows = []
    for artifact in artifact_index:
        rows.append(
            "| {artifact_id} | {name} | {stage} | {type} | {path} |".format(
                artifact_id=artifact.get("artifact_id", "N/A"),
                name=artifact.get("name", "N/A"),
                stage=artifact.get("stage", "N/A"),
                type=artifact.get("type", "N/A"),
                path=artifact.get("path", "N/A"),
            )
        )
    return "\n".join(rows)


def _checkpoint_rows(summary: dict[str, Any]) -> str:
    if summary.get("count", 0) == 0:
        return "- No checkpoints recorded."
    rows = [f"- Checkpoint count: {summary.get('count', 0)}"]
    latest = summary.get("latest")
    if latest:
        rows.append(
            "- Latest checkpoint: {checkpoint_id} ({stage_id}, {status})".format(
                checkpoint_id=latest.get("checkpoint_id", "unknown"),
                stage_id=latest.get("stage_id", "unknown"),
                status=latest.get("status", "unknown"),
            )
        )
    stage_ids = summary.get("stage_ids") or []
    if stage_ids:
        rows.append(f"- Checkpoint stages: {', '.join(stage_ids)}")
    return "\n".join(rows)


def _warning_rows(warnings: list[dict[str, Any]]) -> str:
    if not warnings:
        return "- None."
    rows = []
    for warning in warnings:
        label = warning.get("type", "warning")
        field = warning.get("field", "unknown")
        replacement = warning.get("replacement")
        if replacement:
            rows.append(f"- {label}: {field} -> {replacement}")
        else:
            rows.append(f"- {label}: {field}")
    return "\n".join(rows)


def _reproduction_notes(manifest: dict[str, Any]) -> str:
    workflow_metadata = manifest["workflow_metadata"]
    figure_provenance = manifest["figure_provenance"]
    writing_refs = manifest["writing_artifact_references"]
    notes = [
        f"- Completed stages: {', '.join(manifest['completed_stages']) if manifest['completed_stages'] else 'none'}",
        f"- Pending stages: {', '.join(manifest['pending_stages']) if manifest['pending_stages'] else 'none'}",
        f"- Workflow status: {workflow_metadata.get('status', 'unknown')}",
        f"- Figure provenance status: {figure_provenance.get('status', 'unknown')}",
        f"- Methods reference: {_format_reference(writing_refs.get('methods'))}",
        f"- Results reference: {_format_reference(writing_refs.get('results'))}",
    ]
    planned_outputs = writing_refs.get("planned_outputs") or {}
    package_path = planned_outputs.get("reproducibility_package")
    manifest_path = planned_outputs.get("reproducibility_manifest")
    if package_path:
        notes.append(f"- Reproducibility package path: {package_path}")
    if manifest_path:
        notes.append(f"- Reproducibility manifest path: {manifest_path}")
    if figure_provenance.get("figures"):
        figure_names = [figure.get("name", "unknown") for figure in figure_provenance["figures"]]
        notes.append(f"- Figures covered: {', '.join(figure_names)}")
    return "\n".join(notes)


def _build_package_markdown(manifest: dict[str, Any]) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8") if TEMPLATE_PATH.exists() else ""
    artifact_index = manifest["artifact_index"]
    workflow_metadata = manifest["workflow_metadata"]
    execution_truth = manifest["execution_truth"]

    variables = {
        "workflow_id": workflow_metadata.get("workflow_id", "unknown"),
        "workflow_type": workflow_metadata.get("workflow_type", "unknown"),
        "current_stage": workflow_metadata.get("current_stage", "unknown"),
        "generated_at": manifest.get("generated_at", "unknown"),
        "artifact_rows": _artifact_rows(artifact_index),
        "dry_run_default": execution_truth.get("dry_run", True),
        "real_submit_executed": execution_truth.get("real_submit", False),
        "approval_required_for_real_submit": execution_truth.get("approval_required_for_real_submit", True),
        "structure_manifest_ref": _format_reference(_reference_by_name(artifact_index, "structure_manifest.json")),
        "compute_plan_ref": _format_reference(_reference_by_name(artifact_index, "compute_plan.json")),
        "analysis_report_ref": _format_reference(_reference_by_name(artifact_index, "analysis_report.json")),
        "figures_manifest_ref": _format_reference(_reference_by_name(artifact_index, "figures_manifest.json")),
        "checkpoint_rows": _checkpoint_rows(manifest["checkpoint_summary"]),
        "reproduction_notes": _reproduction_notes(manifest),
        "known_limitations": _warning_rows(manifest["warnings"]),
    }

    if template:
        return _render_template(template, variables)

    return "\n".join([
        "# Reproducibility Package",
        "",
        f"- Workflow ID: {variables['workflow_id']}",
        f"- Workflow type: {variables['workflow_type']}",
        f"- Current stage: {variables['current_stage']}",
        f"- Generated at: {variables['generated_at']}",
        "",
        "## Artifact Index",
        "",
        "| Artifact ID | Name | Stage | Type | Path |",
        "|-------------|------|-------|------|------|",
        variables["artifact_rows"],
        "",
        "## Execution Truth",
        "",
        f"- Dry-run default: {variables['dry_run_default']}",
        f"- Real submit executed: {variables['real_submit_executed']}",
        f"- Approval required for real submit: {variables['approval_required_for_real_submit']}",
        "",
        "## Compute and Analysis Provenance",
        "",
        f"- Structure manifest: {variables['structure_manifest_ref']}",
        f"- Compute plan: {variables['compute_plan_ref']}",
        f"- Analysis report: {variables['analysis_report_ref']}",
        f"- Figures manifest: {variables['figures_manifest_ref']}",
        "",
        "## Checkpoints",
        "",
        variables["checkpoint_rows"],
        "",
        "## Reproduction Notes",
        "",
        variables["reproduction_notes"],
        "",
        "## Known Limitations",
        "",
        variables["known_limitations"],
    ])


def build_reproducibility_package(
    workflow_dir: str,
    parent_artifact_ids: list[str] | None = None,
    software: str | None = None,
    write_manifest_json: bool = True,
) -> dict[str, Any]:
    project_root = resolve_project_root_from_workflow_dir(workflow_dir)
    reports_dir = project_root / ".simflow" / "reports" / "reproducibility"
    reports_dir.mkdir(parents=True, exist_ok=True)

    package_path = reports_dir / "reproducibility_package.md"
    manifest_path = reports_dir / "reproducibility_manifest.json"
    planned_outputs = {
        "reproducibility_package": _relative_path(project_root, package_path),
        "reproducibility_manifest": _relative_path(project_root, manifest_path),
    }

    manifest = build_reproducibility_manifest(
        project_root=str(project_root),
        planned_outputs=planned_outputs,
    )
    manifest["generated_at"] = datetime.now(timezone.utc).isoformat()

    package_content = _build_package_markdown(manifest)
    package_path.write_text(package_content, encoding="utf-8")

    if write_manifest_json:
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    parent_artifact_ids = parent_artifact_ids or []
    manifest_artifact = None
    if write_manifest_json:
        manifest_artifact = register_artifact(
            "reproducibility_manifest.json",
            "reproducibility_manifest",
            "writing",
            project_root=str(project_root),
            path=planned_outputs["reproducibility_manifest"],
            parent_artifacts=parent_artifact_ids,
            parameters={"software": software, "output": "manifest"},
            software=software,
        )

    package_parent_artifacts = list(parent_artifact_ids)
    if manifest_artifact is not None:
        package_parent_artifacts.append(manifest_artifact["artifact_id"])

    package_artifact = register_artifact(
        "reproducibility_package.md",
        "reproducibility_package",
        "writing",
        project_root=str(project_root),
        path=planned_outputs["reproducibility_package"],
        parent_artifacts=package_parent_artifacts,
        parameters={"software": software, "output": "package"},
        software=software,
    )

    artifacts = [package_artifact]
    if manifest_artifact is not None:
        artifacts.insert(0, manifest_artifact)

    return {
        "status": "success",
        "artifacts": artifacts,
        "manifest": manifest,
        "outputs": [planned_outputs["reproducibility_package"], *( [planned_outputs["reproducibility_manifest"]] if write_manifest_json else [] )],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build reproducibility package outputs")
    parser.add_argument("--workflow-dir", required=True, help="Path to .simflow directory")
    parser.add_argument("--software", help="Software name for artifact metadata")
    parser.add_argument("--parent-artifact-ids", default="[]", help="JSON list of parent artifact IDs")
    parser.add_argument("--skip-manifest-json", action="store_true", default=False)
    args = parser.parse_args()

    try:
        parent_artifact_ids = json.loads(args.parent_artifact_ids)
        result = build_reproducibility_package(
            args.workflow_dir,
            parent_artifact_ids=parent_artifact_ids,
            software=args.software,
            write_manifest_json=not args.skip_manifest_json,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
