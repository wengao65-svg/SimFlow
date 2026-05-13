#!/usr/bin/env python3
"""Run the canonical writing stage for Milestone D."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from runtime.lib.artifact import list_artifacts, register_artifact
from runtime.lib.proposal_contract import load_proposal_contract
from runtime.lib.state import read_state


def _load_function(relative_script: str, function_name: str, module_name: str):
    script_path = ROOT / relative_script
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return getattr(module, function_name)


BUILD_REPRODUCIBILITY_PACKAGE = _load_function(
    "skills/simflow-writing/scripts/build_reproducibility_package.py",
    "build_reproducibility_package",
    "simflow_build_reproducibility_package",
)
GENERATE_FINAL_HANDOFF = _load_function(
    "skills/simflow-handoff/scripts/generate_final_handoff.py",
    "generate_final_handoff",
    "simflow_generate_final_handoff",
)


REQUIRED_ARTIFACTS = {
    "proposal": "proposal.md",
    "parameter_table": "parameter_table.csv",
    "research_questions": "research_questions.json",
    "structure_manifest": "structure_manifest.json",
    "compute_plan": "compute_plan.json",
    "analysis_report": "analysis_report.json",
    "figures_manifest": "figures_manifest.json",
}


def resolve_project_root_from_workflow_dir(workflow_dir: str) -> Path:
    path = Path(workflow_dir).expanduser().resolve()
    return path.parent if path.name == ".simflow" else path


def _relative_path(project_root: Path, path: Path) -> str:
    return str(path.resolve().relative_to(project_root))


def _latest_artifact(project_root: Path, artifact_name: str) -> dict[str, Any] | None:
    matches = [
        artifact
        for artifact in list_artifacts(project_root=str(project_root))
        if artifact.get("name") == artifact_name
    ]
    return matches[-1] if matches else None


def _resolve_required_artifacts(project_root: Path) -> dict[str, dict[str, Any]]:
    resolved: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    for key, artifact_name in REQUIRED_ARTIFACTS.items():
        artifact = _latest_artifact(project_root, artifact_name)
        if artifact is None:
            missing.append(artifact_name)
            continue
        artifact_path = project_root / artifact["path"]
        if not artifact_path.is_file():
            missing.append(artifact_name)
            continue
        resolved[key] = artifact
    if missing:
        raise FileNotFoundError(f"Missing writing inputs: {', '.join(sorted(set(missing)))}")
    return resolved


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_parameter_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _modeling_summary(structure_manifest: dict[str, Any]) -> list[str]:
    lines = []
    source_mode = structure_manifest.get("source_mode", "unknown")
    structure_files = structure_manifest.get("structure_files", [])
    validation = structure_manifest.get("validation", {})
    lines.append(f"- Source mode: {source_mode}")
    lines.append(f"- Structure files: {', '.join(structure_files) if structure_files else 'none'}")
    lines.append(f"- Validation status: {validation.get('status', 'unknown')}")
    return lines


def _compute_summary(compute_plan: dict[str, Any]) -> list[str]:
    resources = compute_plan.get("resource_estimate", {})
    lines = [
        f"- Task: {compute_plan.get('task', 'unknown')}",
        f"- Scheduler: {compute_plan.get('scheduler', 'unknown')}",
        f"- Recommended command: {compute_plan.get('recommended_command', 'unknown')}",
        f"- Dry-run: {compute_plan.get('dry_run', True)}",
        f"- Real submit: {compute_plan.get('real_submit', False)}",
    ]
    if resources:
        lines.append(
            "- Resource estimate: "
            f"nodes={resources.get('recommended_nodes', 'n/a')}, "
            f"ntasks={resources.get('recommended_ntasks', 'n/a')}, "
            f"walltime={resources.get('walltime_hours', 'n/a')}h"
        )
    return lines


def _parameter_summary(rows: list[dict[str, str]], limit: int = 8) -> list[str]:
    if not rows:
        return ["- No parameter rows available."]
    lines = [f"- Total parameters: {len(rows)}"]
    for row in rows[:limit]:
        parameter = row.get("parameter", "")
        value = row.get("value", "")
        if parameter:
            lines.append(f"- {parameter}: {value}")
    if len(rows) > limit:
        lines.append(f"- ... ({len(rows) - limit} more)")
    return lines


def _analysis_summary(analysis_report: dict[str, Any]) -> list[str]:
    status = analysis_report.get("status", "unknown")
    lines = [
        f"- Status: {status}",
        f"- Software: {analysis_report.get('software', 'unknown')}",
        f"- Task: {analysis_report.get('task', 'unknown')}",
        f"- Conclusions: {analysis_report.get('conclusions', 'n/a')}",
    ]
    if status != "completed":
        lines.append("- Note: Analysis outputs are not fully ready; this summary reflects degraded/waiting state.")
    return lines


def _visualization_summary(figures_manifest: dict[str, Any]) -> list[str]:
    status = figures_manifest.get("status", "unknown")
    figures = figures_manifest.get("figures", [])
    lines = [
        f"- Status: {status}",
    ]
    if figures:
        lines.append("- Figures:")
        for figure in figures:
            lines.append(f"  - {figure.get('name', 'unknown')} ({figure.get('title', 'untitled')})")
    else:
        skipped = figures_manifest.get("skipped_reasons", [])
        lines.append("- Figures: none")
        if skipped:
            lines.append(f"- Skipped reasons: {'; '.join(skipped)}")
    if status != "completed":
        lines.append("- Note: Visualization remains degraded or waiting; no finalized figure conclusions are claimed.")
    return lines


def run_writing_stage(workflow_dir: str, params: dict | None = None, dry_run: bool = False) -> dict:
    project_root = resolve_project_root_from_workflow_dir(workflow_dir)
    state = read_state(project_root=str(project_root), state_file="workflow.json")
    if not state:
        return {"status": "error", "message": "No workflow state found"}

    params = params or {}

    try:
        contract = load_proposal_contract(str(project_root / ".simflow"))
        required_artifacts = _resolve_required_artifacts(project_root)
    except Exception as exc:
        return {"status": "error", "message": str(exc)}

    parent_artifact_ids = [
        required_artifacts[key]["artifact_id"]
        for key in (
            "proposal",
            "parameter_table",
            "research_questions",
            "structure_manifest",
            "compute_plan",
            "analysis_report",
            "figures_manifest",
        )
    ]

    proposal_path = project_root / required_artifacts["proposal"]["path"]
    parameter_table_path = project_root / required_artifacts["parameter_table"]["path"]
    structure_manifest_path = project_root / required_artifacts["structure_manifest"]["path"]
    compute_plan_path = project_root / required_artifacts["compute_plan"]["path"]
    analysis_report_path = project_root / required_artifacts["analysis_report"]["path"]
    figures_manifest_path = project_root / required_artifacts["figures_manifest"]["path"]

    parameter_rows = _read_parameter_rows(parameter_table_path)
    structure_manifest = _read_json(structure_manifest_path)
    compute_plan = _read_json(compute_plan_path)
    analysis_report = _read_json(analysis_report_path)
    figures_manifest = _read_json(figures_manifest_path)

    methods_path = project_root / ".simflow" / "reports" / "writing" / "methods.md"
    results_path = project_root / ".simflow" / "reports" / "writing" / "results.md"
    reproducibility_package_path = project_root / ".simflow" / "reports" / "reproducibility" / "reproducibility_package.md"
    reproducibility_manifest_path = project_root / ".simflow" / "reports" / "reproducibility" / "reproducibility_manifest.json"
    final_handoff_markdown_path = project_root / ".simflow" / "reports" / "handoff" / "final_handoff.md"
    final_handoff_json_path = project_root / ".simflow" / "reports" / "handoff" / "final_handoff.json"
    methods_rel = _relative_path(project_root, methods_path)
    results_rel = _relative_path(project_root, results_path)
    reproducibility_package_rel = _relative_path(project_root, reproducibility_package_path)
    reproducibility_manifest_rel = _relative_path(project_root, reproducibility_manifest_path)
    final_handoff_markdown_rel = _relative_path(project_root, final_handoff_markdown_path)
    final_handoff_json_rel = _relative_path(project_root, final_handoff_json_path)

    manifest: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "workflow_type": contract.get("workflow_type"),
        "software": contract.get("software"),
        "material": contract.get("material"),
        "analysis_status": analysis_report.get("status"),
        "visualization_status": figures_manifest.get("status"),
        "source_artifact_ids": parent_artifact_ids,
        "status": "planned" if dry_run else "completed",
        "outputs": [
            methods_rel,
            results_rel,
            reproducibility_package_rel,
            final_handoff_markdown_rel,
            final_handoff_json_rel,
        ],
        "auxiliary_outputs": [reproducibility_manifest_rel],
    }

    if dry_run:
        return {
            "status": "dry_run_complete",
            "manifest": manifest,
            "inputs": parent_artifact_ids,
            "planned_outputs": [
                methods_rel,
                results_rel,
                reproducibility_package_rel,
                final_handoff_markdown_rel,
                final_handoff_json_rel,
            ],
            "auxiliary_outputs": [reproducibility_manifest_rel],
        }

    methods_path.parent.mkdir(parents=True, exist_ok=True)

    methods_content = "\n".join([
        "# Methods",
        "",
        "## Research Goal",
        contract.get("research_goal") or "Not specified.",
        "",
        "## System and Material",
        f"- Material: {contract.get('material', 'Not specified')}",
        "",
        "## Software",
        f"- Software: {contract.get('software', 'unknown')}",
        "",
        "## Modeling Summary",
        *_modeling_summary(structure_manifest),
        "",
        "## Compute Configuration",
        *_compute_summary(compute_plan),
        "",
        "## Parameter Table Summary",
        *_parameter_summary(parameter_rows),
        "",
        "## Source Artifact IDs",
        *(f"- {artifact_id}" for artifact_id in parent_artifact_ids),
        "",
        "## Proposal Reference",
        f"- Path: {_relative_path(project_root, proposal_path)}",
    ])
    methods_path.write_text(methods_content, encoding="utf-8")

    results_content = "\n".join([
        "# Results",
        "",
        "## Analysis Summary",
        *_analysis_summary(analysis_report),
        "",
        "## Visualization Summary",
        *_visualization_summary(figures_manifest),
        "",
        "## Traceability / Source Artifact IDs",
        *(f"- {artifact_id}" for artifact_id in parent_artifact_ids),
    ])
    results_path.write_text(results_content, encoding="utf-8")

    methods_artifact = register_artifact(
        "methods.md",
        "methods",
        "writing",
        project_root=str(project_root),
        path=methods_rel,
        parent_artifacts=parent_artifact_ids,
        parameters={
            "software": contract.get("software"),
            "material": contract.get("material"),
            "analysis_status": analysis_report.get("status"),
            "visualization_status": figures_manifest.get("status"),
        },
        software=contract.get("software"),
    )
    results_artifact = register_artifact(
        "results.md",
        "results",
        "writing",
        project_root=str(project_root),
        path=results_rel,
        parent_artifacts=[methods_artifact["artifact_id"], *parent_artifact_ids],
        parameters={
            "software": contract.get("software"),
            "material": contract.get("material"),
            "analysis_status": analysis_report.get("status"),
            "visualization_status": figures_manifest.get("status"),
        },
        software=contract.get("software"),
    )
    reproducibility_result = BUILD_REPRODUCIBILITY_PACKAGE(
        str(project_root / ".simflow"),
        parent_artifact_ids=[methods_artifact["artifact_id"], results_artifact["artifact_id"], *parent_artifact_ids],
        software=contract.get("software"),
        write_manifest_json=True,
    )
    if reproducibility_result.get("status") != "success":
        return {"status": "error", "message": "Failed to build reproducibility package"}

    reproducibility_manifest_artifact = next(
        artifact for artifact in reproducibility_result["artifacts"] if artifact["name"] == "reproducibility_manifest.json"
    )
    reproducibility_package_artifact = next(
        artifact for artifact in reproducibility_result["artifacts"] if artifact["name"] == "reproducibility_package.md"
    )
    final_handoff_result = GENERATE_FINAL_HANDOFF(
        str(project_root / ".simflow"),
        source_artifact_ids=parent_artifact_ids,
        parent_artifact_ids=[
            methods_artifact["artifact_id"],
            results_artifact["artifact_id"],
            reproducibility_package_artifact["artifact_id"],
            reproducibility_manifest_artifact["artifact_id"],
            *parent_artifact_ids,
        ],
        software=contract.get("software"),
    )
    if final_handoff_result.get("status") != "success":
        return {"status": "error", "message": "Failed to build final handoff deliverables"}

    return {
        "status": "success",
        "artifacts": [
            methods_artifact,
            results_artifact,
            reproducibility_package_artifact,
            *final_handoff_result["artifacts"],
        ],
        "manifest": manifest,
        "inputs": parent_artifact_ids,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the canonical writing stage")
    parser.add_argument("--workflow-dir", required=True, help="Path to .simflow directory")
    parser.add_argument("--params", type=str, default="{}", help="JSON parameters for the stage")
    parser.add_argument("--dry-run", action="store_true", default=False)
    args = parser.parse_args()

    try:
        params = json.loads(args.params)
        result = run_writing_stage(args.workflow_dir, params=params, dry_run=args.dry_run)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
