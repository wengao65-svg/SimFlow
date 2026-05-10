#!/usr/bin/env python3
"""Run the canonical analysis stage for Milestone C."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from runtime.lib.artifact import get_artifact, register_artifact
from runtime.lib.parsers.cp2k_parser import CP2KParser
from runtime.lib.proposal_contract import load_proposal_contract
from runtime.lib.state import read_state


def resolve_project_root_from_workflow_dir(workflow_dir: str) -> Path:
    path = Path(workflow_dir).expanduser().resolve()
    return path.parent if path.name == ".simflow" else path


def _load_function(relative_script: str, function_name: str, module_name: str):
    script_path = ROOT / relative_script
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return getattr(module, function_name)


ANALYZE_RESULTS = _load_function(
    "skills/simflow-analysis/scripts/analyze_dft_results.py",
    "analyze_results",
    "simflow_analyze_dft_results",
)
GENERATE_REPORT = _load_function(
    "skills/simflow-analysis/scripts/generate_analysis_report.py",
    "generate_report",
    "simflow_generate_analysis_report",
)


def _stage_output_artifacts(project_root: Path, stage_name: str) -> list[dict[str, Any]]:
    stages_state = read_state(project_root=str(project_root), state_file="stages.json")
    output_ids = stages_state.get(stage_name, {}).get("outputs", [])
    artifacts = []
    for artifact_id in output_ids:
        artifact = get_artifact(artifact_id, project_root=str(project_root))
        if artifact:
            artifacts.append(artifact)
    return artifacts


def _relative_path(project_root: Path, path: Path) -> str:
    return str(path.resolve().relative_to(project_root))


def _trajectory_status(task: str, source_files: list[str]) -> dict[str, Any]:
    if task not in {"md", "aimd", "aimd_nvt", "aimd_nve", "aimd_npt"}:
        return {"status": "not_requested"}
    if not any(path.endswith(("XDATCAR", ".xyz")) for path in source_files):
        return {"status": "missing_trajectory"}
    if importlib.util.find_spec("MDAnalysis") is None:
        return {
            "status": "skipped_optional_dependency",
            "dependency": "MDAnalysis",
            "reason": "MDAnalysis is not installed.",
        }
    return {"status": "available"}


def _analyze_vasp(calc_dir: Path) -> tuple[str, dict[str, Any]]:
    candidates = [
        calc_dir / "vasprun.xml",
        calc_dir / "OUTCAR",
        calc_dir / "OSZICAR",
        calc_dir / "EIGENVAL",
    ]
    output_files = [str(path) for path in candidates if path.is_file()]
    if not output_files:
        return "waiting_for_outputs", {
            "status": "waiting_for_outputs",
            "source_files": [],
            "raw_results": None,
            "conclusions": "Compute outputs are not available yet.",
        }

    analysis = ANALYZE_RESULTS("vasp", output_files)
    primary = next((item for item in analysis["results"] if item.get("status") == "success"), {})
    return "completed", {
        "status": "completed",
        "source_files": [_relative_path(calc_dir.parents[2], Path(path)) for path in output_files],
        "raw_results": analysis,
        "final_energy": analysis.get("final_energy"),
        "total_energy": primary.get("total_energy"),
        "energy_converged": analysis.get("all_converged"),
        "job_type": primary.get("job_type"),
        "warnings": primary.get("warnings", []),
        "errors": primary.get("errors", []),
        "conclusions": "Parsed VASP outputs successfully.",
    }


def _analyze_cp2k(calc_dir: Path) -> tuple[str, dict[str, Any]]:
    parser = CP2KParser()
    parsed = parser.parse_outputs(str(calc_dir))
    if parsed["status"] == "missing_outputs":
        return "waiting_for_outputs", {
            "status": "waiting_for_outputs",
            "source_files": [],
            "raw_results": parsed,
            "conclusions": "Compute outputs are not available yet.",
        }

    source_files = [
        _relative_path(calc_dir.parents[2], Path(path))
        for path in parsed["files"].values()
        if path
    ]
    summary = parsed.get("summary", {})
    return "completed", {
        "status": "completed",
        "source_files": source_files,
        "raw_results": parsed,
        "final_energy": summary.get("final_energy"),
        "total_energy": summary.get("final_energy"),
        "temperature": summary.get("temperature"),
        "trajectory_steps": summary.get("md_steps"),
        "energy_converged": summary.get("normal_end", False),
        "warnings": parsed.get("log", {}).get("warnings", []),
        "errors": parsed.get("log", {}).get("errors", []),
        "conclusions": "Parsed CP2K outputs successfully.",
    }


def run_analysis_stage(workflow_dir: str, params: dict | None = None, dry_run: bool = False) -> dict:
    project_root = resolve_project_root_from_workflow_dir(workflow_dir)
    state = read_state(project_root=str(project_root), state_file="workflow.json")
    if not state:
        return {"status": "error", "message": "No workflow state found"}

    contract = load_proposal_contract(str(project_root / ".simflow"))
    compute_artifacts = _stage_output_artifacts(project_root, "compute")
    if not compute_artifacts:
        return {"status": "error", "message": "Compute stage has no registered outputs"}

    compute_plan_artifact = next((artifact for artifact in compute_artifacts if artifact.get("type") == "compute_plan"), None)
    if not compute_plan_artifact:
        return {"status": "error", "message": "Compute plan is missing"}

    compute_plan_path = project_root / compute_plan_artifact["path"]
    compute_plan = json.loads(compute_plan_path.read_text(encoding="utf-8"))
    software = contract["software"]
    task = compute_plan.get("task") or contract.get("task") or contract.get("job_type") or "unknown"
    calc_dir = project_root / ".simflow" / "artifacts" / "compute"
    parent_artifact_ids = [artifact["artifact_id"] for artifact in compute_artifacts]

    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "software": software,
        "task": task,
        "compute_plan_artifact_id": compute_plan_artifact["artifact_id"],
        "parent_artifact_ids": parent_artifact_ids,
        "status": "planned" if dry_run else "waiting_for_outputs",
        "source_files": [],
    }

    if dry_run:
        return {
            "status": "dry_run_complete",
            "manifest": report,
            "inputs": parent_artifact_ids,
            "planned_outputs": [
                ".simflow/reports/analysis/analysis_report.json",
                ".simflow/reports/analysis/analysis_report.md",
            ],
        }

    if software == "vasp":
        status, details = _analyze_vasp(calc_dir)
    elif software == "cp2k":
        status, details = _analyze_cp2k(calc_dir)
    else:
        return {"status": "error", "message": f"Unsupported software for analysis stage: {software}"}

    report.update(details)
    report["status"] = status
    report["optional_trajectory_analysis"] = _trajectory_status(task, report.get("source_files", []))

    reports_dir = project_root / ".simflow" / "reports" / "analysis"
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / "analysis_report.json"
    markdown_path = reports_dir / "analysis_report.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    GENERATE_REPORT(report, str(markdown_path))

    json_artifact = register_artifact(
        "analysis_report.json",
        "analysis_report",
        "analysis",
        project_root=str(project_root),
        path=_relative_path(project_root, json_path),
        parent_artifacts=parent_artifact_ids,
        parameters={"software": software, "task": task, "status": report["status"]},
        software=software,
    )
    markdown_artifact = register_artifact(
        "analysis_report.md",
        "analysis_markdown",
        "analysis",
        project_root=str(project_root),
        path=_relative_path(project_root, markdown_path),
        parent_artifacts=[json_artifact["artifact_id"]],
        parameters={"software": software, "task": task, "status": report["status"]},
        software=software,
    )

    return {
        "status": "success",
        "artifacts": [json_artifact, markdown_artifact],
        "manifest": report,
        "inputs": parent_artifact_ids,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the canonical analysis stage")
    parser.add_argument("--workflow-dir", required=True, help="Path to .simflow directory")
    parser.add_argument("--params", type=str, default="{}", help="JSON parameters for the stage")
    parser.add_argument("--dry-run", action="store_true", default=False)
    args = parser.parse_args()

    try:
        params = json.loads(args.params)
        result = run_analysis_stage(args.workflow_dir, params=params, dry_run=args.dry_run)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
