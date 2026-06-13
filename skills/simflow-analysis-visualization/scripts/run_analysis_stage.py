#!/usr/bin/env python3
"""Run the built-in optional analysis stage runner for Milestone C."""

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

from runtime.simflow_core.artifacts import get_artifact, register_artifact
from runtime.simflow_core.proposals import capability_warning, load_proposal_contract
from runtime.simflow_core.state import read_state
from runtime.simflow_helpers.engines.cp2k import CP2KParser
from runtime.simflow_helpers.engines.parsers.lammps_parser import LAMMPSParser


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
    "skills/simflow-analysis-visualization/scripts/analyze_dft_results.py",
    "analyze_results",
    "simflow_analyze_dft_results",
)
GENERATE_REPORT = _load_function(
    "skills/simflow-analysis-visualization/scripts/generate_analysis_report.py",
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


def _as_path_values(value: Any) -> list[str]:
    if value in (None, "", False):
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [str(item) for item in value.values() if item]
    if isinstance(value, (list, tuple)):
        values: list[str] = []
        for item in value:
            if isinstance(item, dict) and item.get("path"):
                values.append(str(item["path"]))
            elif item:
                values.append(str(item))
        return values
    return []


def _direct_output_values(contract: dict[str, Any], params: dict[str, Any]) -> list[str]:
    merged = {**contract.get("parameter_overrides", {}), **(params or {})}
    values: list[str] = []
    for key in ("output_files", "existing_output_files", "compute_outputs", "analysis_inputs"):
        values.extend(_as_path_values(merged.get(key)))
    output_dir = merged.get("output_dir") or merged.get("calculation_dir")
    if output_dir:
        values.append(str(output_dir))
    return list(dict.fromkeys(values))


def _resolve_direct_output_files(project_root: Path, values: list[str]) -> list[Path]:
    resolved: list[Path] = []
    for value in values:
        path = Path(value).expanduser()
        path = path if path.is_absolute() else project_root / path
        if path.is_dir():
            for child_name in (
                "vasprun.xml",
                "OUTCAR",
                "OSZICAR",
                "EIGENVAL",
                "cp2k.out",
                "cp2k.log",
                "log.lammps",
                "lammps.log",
                "dump.lammps",
                "data.lammps",
            ):
                child = path / child_name
                if child.is_file():
                    resolved.append(child.resolve())
            continue
        if path.is_file():
            resolved.append(path.resolve())
    return list(dict.fromkeys(resolved))


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


def _analyze_vasp_files(project_root: Path, output_files: list[Path]) -> tuple[str, dict[str, Any]]:
    if not output_files:
        return "waiting_for_outputs", {
            "status": "waiting_for_outputs",
            "source_files": [],
            "raw_results": None,
            "conclusions": "Compute outputs are not available yet.",
        }

    analysis = ANALYZE_RESULTS("vasp", [str(path) for path in output_files])
    primary = next((item for item in analysis["results"] if item.get("status") == "success"), {})
    status = "completed" if analysis.get("num_successful", 0) else "waiting_for_outputs"
    return status, {
        "status": status,
        "source_files": [_relative_path(project_root, path) for path in output_files],
        "raw_results": analysis,
        "final_energy": analysis.get("final_energy"),
        "total_energy": primary.get("total_energy"),
        "energy_converged": analysis.get("all_converged"),
        "job_type": primary.get("job_type"),
        "warnings": primary.get("warnings", []),
        "errors": primary.get("errors", []),
        "conclusions": "Parsed user-provided VASP outputs successfully."
        if status == "completed"
        else "User-provided VASP outputs could not be parsed.",
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


def _analyze_lammps_files(project_root: Path, output_files: list[Path]) -> tuple[str, dict[str, Any]]:
    log_files = [path for path in output_files if path.name in {"log.lammps", "lammps.log"} or "log" in path.name.lower()]
    dump_files = [path for path in output_files if "dump" in path.name.lower()]
    data_files = [path for path in output_files if path.name.endswith(".data") or path.name == "data.lammps"]
    if not log_files:
        return "waiting_for_outputs", {
            "status": "waiting_for_outputs",
            "source_files": [_relative_path(project_root, path) for path in output_files],
            "raw_results": None,
            "warnings": [{"code": "missing_lammps_log", "message": "No LAMMPS log file was provided."}],
            "errors": [],
            "conclusions": "LAMMPS outputs are incomplete; no log file was available for parsing.",
        }

    parser = LAMMPSParser()
    parsed = []
    for path in log_files:
        item = parser.parse(str(path))
        parsed.append({
            "file": _relative_path(project_root, path),
            "status": "success",
            "job_type": item.job_type,
            "converged": item.converged,
            "final_energy": item.final_energy,
            "parameters": item.parameters,
            "metadata": item.metadata,
            "warnings": item.warnings,
            "errors": item.errors,
        })
    primary = parsed[-1]
    warnings = []
    if not dump_files:
        warnings.append({"code": "missing_lammps_dump", "message": "No trajectory dump was provided; trajectory analyses are unavailable."})
    if not data_files:
        warnings.append({"code": "missing_lammps_data", "message": "No data file was provided; atom typing and masses may be unavailable."})
    return "completed", {
        "status": "completed",
        "source_files": [_relative_path(project_root, path) for path in output_files],
        "raw_results": {"software": "lammps", "results": parsed},
        "final_energy": primary.get("final_energy"),
        "total_energy": primary.get("final_energy"),
        "temperature": primary.get("metadata", {}).get("final_temp"),
        "trajectory_steps": primary.get("metadata", {}).get("total_steps"),
        "energy_converged": primary.get("converged"),
        "warnings": [*warnings, *primary.get("warnings", [])],
        "errors": primary.get("errors", []),
        "conclusions": "Parsed user-provided LAMMPS log evidence successfully.",
    }


def run_analysis_stage(workflow_dir: str, params: dict | None = None, dry_run: bool = False) -> dict:
    project_root = resolve_project_root_from_workflow_dir(workflow_dir)
    state = read_state(project_root=str(project_root), state_file="workflow.json")
    if not state:
        return {"status": "error", "message": "No workflow state found"}

    params = params or {}
    contract = load_proposal_contract(str(project_root / ".simflow"), allow_direct_entry=True)
    compute_artifacts = _stage_output_artifacts(project_root, "computation")
    direct_output_files = _resolve_direct_output_files(
        project_root,
        _direct_output_values(contract, params),
    ) if not compute_artifacts else []
    if not compute_artifacts and not direct_output_files:
        return {"status": "error", "message": "Compute stage has no registered outputs"}

    compute_plan_artifact = next((artifact for artifact in compute_artifacts if artifact.get("type") == "compute_plan"), None)
    if compute_artifacts and not compute_plan_artifact:
        return {"status": "error", "message": "Compute plan is missing"}

    compute_plan = {}
    if compute_plan_artifact:
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
        "compute_plan_artifact_id": compute_plan_artifact["artifact_id"] if compute_plan_artifact else None,
        "parent_artifact_ids": parent_artifact_ids,
        "compute_context": "registered_compute_artifacts" if compute_artifacts else "user_provided_outputs",
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

    direct_output_artifacts: list[dict[str, Any]] = []
    if direct_output_files:
        direct_output_artifacts = [
            register_artifact(
                path.name,
                "user_provided_compute_output",
                "analysis_visualization",
                project_root=str(project_root),
                path=_relative_path(project_root, path),
                parent_artifacts=[],
                parameters={"software": software, "task": task},
                software=software,
                metadata={"source": "user_provided"},
            )
            for path in direct_output_files
        ]
        parent_artifact_ids = [artifact["artifact_id"] for artifact in direct_output_artifacts]
        report["parent_artifact_ids"] = parent_artifact_ids

    if software == "vasp":
        status, details = _analyze_vasp_files(project_root, direct_output_files) if direct_output_files else _analyze_vasp(calc_dir)
        analysis_script = "skills/simflow-analysis-visualization/scripts/analyze_dft_results.py"
    elif software == "cp2k":
        status, details = _analyze_cp2k(calc_dir)
        analysis_script = "runtime/simflow_helpers/engines/cp2k"
    elif software == "lammps":
        status, details = _analyze_lammps_files(project_root, direct_output_files)
        analysis_script = "runtime/simflow_helpers/engines/parsers/lammps_parser.py"
    else:
        return capability_warning(contract, "analysis_visualization", "analysis", software)

    report.update(details)
    report["status"] = status
    report["optional_trajectory_analysis"] = _trajectory_status(task, report.get("source_files", []))

    reports_dir = project_root / ".simflow" / "reports" / "analysis"
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / "analysis_report.json"
    markdown_path = reports_dir / "analysis_report.md"
    report["analysis_provenance"] = {
        "input_artifact_ids": parent_artifact_ids,
        "compute_plan_artifact_id": compute_plan_artifact["artifact_id"] if compute_plan_artifact else None,
        "analysis_script": analysis_script,
        "report_script": "skills/simflow-analysis-visualization/scripts/generate_analysis_report.py",
        "source_files": report.get("source_files", []),
        "output_files": [
            _relative_path(project_root, json_path),
            _relative_path(project_root, markdown_path),
        ],
    }
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    GENERATE_REPORT(report, str(markdown_path))

    json_artifact = register_artifact(
        "analysis_report.json",
        "analysis_report",
        "analysis_visualization",
        project_root=str(project_root),
        path=_relative_path(project_root, json_path),
        parent_artifacts=parent_artifact_ids,
        parameters={"software": software, "task": task, "status": report["status"]},
        software=software,
        metadata={"evidence_key": "analysis_outputs"},
    )
    markdown_artifact = register_artifact(
        "analysis_report.md",
        "analysis_markdown",
        "analysis_visualization",
        project_root=str(project_root),
        path=_relative_path(project_root, markdown_path),
        parent_artifacts=[json_artifact["artifact_id"]],
        parameters={"software": software, "task": task, "status": report["status"]},
        software=software,
    )

    return {
        "status": "success",
        "artifacts": [*direct_output_artifacts, json_artifact, markdown_artifact],
        "manifest": report,
        "inputs": parent_artifact_ids,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the built-in optional analysis stage runner")
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
