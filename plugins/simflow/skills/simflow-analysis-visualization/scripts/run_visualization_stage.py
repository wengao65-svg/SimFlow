#!/usr/bin/env python3
"""Run the built-in optional visualization stage runner for Milestone C."""

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

from runtime.simflow_core.artifacts import get_artifact, list_artifacts, register_artifact
from runtime.simflow_core.proposals import load_proposal_contract
from runtime.simflow_core.state import read_state
from runtime.simflow_core.toolchains import capability_warning
from runtime.simflow_helpers.engines.cp2k import CP2KParser


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


def _stage_output_artifacts(project_root: Path, stage_name: str) -> list[dict[str, Any]]:
    stages_state = read_state(project_root=str(project_root), state_file="stages.json")
    output_ids = stages_state.get(stage_name, {}).get("outputs", [])
    artifacts = []
    for artifact_id in output_ids:
        artifact = get_artifact(artifact_id, project_root=str(project_root))
        if artifact:
            artifacts.append(artifact)
    if not artifacts:
        artifacts = list_artifacts(stage=stage_name, project_root=str(project_root))
    return artifacts


def _relative_path(project_root: Path, path: Path) -> str:
    return str(path.resolve().relative_to(project_root))


def _aggregate_visual_qa_status(statuses: list[str]) -> str:
    if not statuses:
        return "skipped"
    if any(status == "error" for status in statuses):
        return "error"
    if any(status == "warning" for status in statuses):
        return "warning"
    if all(status == "passed" for status in statuses):
        return "passed"
    if all(status == "skipped_optional_dependency" for status in statuses):
        return "skipped_optional_dependency"
    return "review_needed"


def _visual_qa_skipped(reason: str, status: str = "skipped") -> dict[str, Any]:
    return {
        "status": status,
        "checks": {},
        "warnings": [],
        "figures": [],
        "skipped_reason": reason,
    }


def run_visualization_stage(workflow_dir: str, params: dict | None = None, dry_run: bool = True) -> dict:
    project_root = resolve_project_root_from_workflow_dir(workflow_dir)
    state = read_state(project_root=str(project_root), state_file="workflow.json")
    if not state:
        return {"status": "error", "message": "No workflow state found"}

    contract = load_proposal_contract(str(project_root / ".simflow"), allow_direct_entry=True)
    analysis_artifacts = _stage_output_artifacts(project_root, "analysis_visualization")
    if not analysis_artifacts:
        return {"status": "error", "message": "Analysis stage has no registered outputs"}

    analysis_report_artifact = next((artifact for artifact in analysis_artifacts if artifact.get("type") == "analysis_report"), None)
    if not analysis_report_artifact:
        return {"status": "error", "message": "Analysis report is missing"}

    analysis_report_path = project_root / analysis_report_artifact["path"]
    analysis_report = json.loads(analysis_report_path.read_text(encoding="utf-8"))
    software = contract["software"]
    task = analysis_report.get("task") or contract.get("task") or contract.get("job_type") or "unknown"
    parent_artifact_ids = [artifact["artifact_id"] for artifact in analysis_artifacts]

    manifest: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "software": software,
        "task": task,
        "analysis_artifact_ids": parent_artifact_ids,
        "analysis_report_artifact_id": analysis_report_artifact["artifact_id"],
        "status": "planned" if dry_run else "waiting_for_outputs",
        "renderer": {
            "matplotlib": importlib.util.find_spec("matplotlib") is not None,
        },
        "figure_traceability": {
            "analysis_report_artifact_id": analysis_report_artifact["artifact_id"],
            "input_artifact_ids": parent_artifact_ids,
            "source_files": analysis_report.get("source_files", []),
            "plotting_script": "skills/simflow-analysis-visualization/scripts/plot_energy_curve.py",
            "figures": [],
        },
        "figures": [],
        "visual_qa": _visual_qa_skipped("Visualization has not rendered figures yet.", status="planned"),
        "skipped_reasons": [],
    }

    if dry_run:
        return {
            "status": "dry_run_complete",
            "manifest": manifest,
            "inputs": parent_artifact_ids,
            "planned_outputs": [
                ".simflow/reports/visualization/figures_manifest.json",
                ".simflow/artifacts/visualization",
            ],
        }

    reports_dir = project_root / ".simflow" / "reports" / "visualization"
    figures_dir = project_root / ".simflow" / "artifacts" / "visualization"
    reports_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    if analysis_report.get("status") != "completed":
        manifest["status"] = "waiting_for_outputs"
        manifest["skipped_reasons"].append("Analysis outputs are not ready for visualization.")
    elif not manifest["renderer"]["matplotlib"]:
        manifest["status"] = "skipped_optional_dependency"
        manifest["skipped_reasons"].append("matplotlib is not installed.")
    else:
        parse_energies = _load_function(
            "skills/simflow-analysis-visualization/scripts/plot_energy_curve.py",
            "parse_energies",
            "simflow_parse_energies",
        )
        plot_energy_curve = _load_function(
            "skills/simflow-analysis-visualization/scripts/plot_energy_curve.py",
            "plot_energy_curve",
            "simflow_plot_energy_curve",
        )
        source_files = [project_root / rel_path for rel_path in analysis_report.get("source_files", [])]
        figure_path = figures_dir / "energy_convergence.png"

        if software == "vasp":
            energy_file = next((path for path in source_files if path.name == "OSZICAR" and path.is_file()), None)
            if energy_file is None:
                manifest["status"] = "no_plot_data"
                manifest["skipped_reasons"].append("OSZICAR is not available for plotting.")
            else:
                data = parse_energies(str(energy_file), "vasp")
                if not data["energies"]:
                    manifest["status"] = "no_plot_data"
                    manifest["skipped_reasons"].append("OSZICAR did not contain plottable energies.")
                else:
                    result = plot_energy_curve(data["energies"], data["steps"], str(figure_path), title="VASP Energy Convergence", software="vasp")
                    manifest["status"] = "completed"
                    manifest["figures"].append({
                        "name": figure_path.name,
                        "path": _relative_path(project_root, figure_path),
                        "title": "VASP Energy Convergence",
                        "num_steps": result["num_steps"],
                        "source_data": _relative_path(project_root, energy_file),
                        "plotting_script": "skills/simflow-analysis-visualization/scripts/plot_energy_curve.py",
                        "analysis_report_artifact_id": analysis_report_artifact["artifact_id"],
                    })
        elif software == "cp2k":
            ener_file = next((path for path in source_files if path.suffix == ".ener" and path.is_file()), None)
            if ener_file is None:
                manifest["status"] = "no_plot_data"
                manifest["skipped_reasons"].append("CP2K .ener file is not available for plotting.")
            else:
                ener_data = CP2KParser().parse_ener(str(ener_file))
                if not ener_data["steps"]:
                    manifest["status"] = "no_plot_data"
                    manifest["skipped_reasons"].append("CP2K .ener file did not contain plottable energies.")
                else:
                    result = plot_energy_curve(
                        ener_data["potential"],
                        ener_data["steps"],
                        str(figure_path),
                        title="CP2K Energy Trace",
                        software="cp2k",
                    )
                    manifest["status"] = "completed"
                    manifest["figures"].append({
                        "name": figure_path.name,
                        "path": _relative_path(project_root, figure_path),
                        "title": "CP2K Energy Trace",
                        "num_steps": result["num_steps"],
                        "source_data": _relative_path(project_root, ener_file),
                        "plotting_script": "skills/simflow-analysis-visualization/scripts/plot_energy_curve.py",
                        "analysis_report_artifact_id": analysis_report_artifact["artifact_id"],
                    })
        elif software == "lammps":
            log_file = next(
                (
                    path
                    for path in source_files
                    if path.is_file()
                    and (path.name in {"log.lammps", "lammps.log"} or "log" in path.name.lower())
                ),
                None,
            )
            if log_file is None:
                manifest["status"] = "no_plot_data"
                manifest["skipped_reasons"].append("LAMMPS log file is not available for plotting.")
            else:
                data = parse_energies(str(log_file), "lammps")
                if not data["energies"]:
                    manifest["status"] = "no_plot_data"
                    manifest["skipped_reasons"].append(
                        "LAMMPS log did not contain plottable thermo potential-energy data."
                    )
                else:
                    result = plot_energy_curve(
                        data["energies"],
                        data["steps"],
                        str(figure_path),
                        title="LAMMPS Potential Energy Trace",
                        software="lammps",
                    )
                    manifest["status"] = "completed"
                    manifest["figures"].append({
                        "name": figure_path.name,
                        "path": _relative_path(project_root, figure_path),
                        "title": "LAMMPS Potential Energy Trace",
                        "num_steps": result["num_steps"],
                        "source_data": _relative_path(project_root, log_file),
                        "plotting_script": "skills/simflow-analysis-visualization/scripts/plot_energy_curve.py",
                        "analysis_report_artifact_id": analysis_report_artifact["artifact_id"],
                    })
        else:
            return capability_warning(contract, "analysis_visualization", "visualization", software)

    qa_artifacts = []
    if manifest["figures"]:
        try:
            audit_figure = _load_function(
                "skills/simflow-analysis-visualization/scripts/audit_figure.py",
                "audit_figure",
                "simflow_audit_figure",
            )
            qa_entries: list[dict[str, Any]] = []
            qa_statuses: list[str] = []
            qa_warnings: list[str] = []
            for figure in manifest["figures"]:
                figure_path = project_root / figure["path"]
                audit_path = reports_dir / f"{Path(figure['name']).stem}_visual_qa.json"
                audit = audit_figure(str(figure_path), str(audit_path))
                qa_artifact = register_artifact(
                    audit_path.name,
                    "visual_qa_report",
                    "analysis_visualization",
                    project_root=str(project_root),
                    path=_relative_path(project_root, audit_path),
                    parent_artifacts=parent_artifact_ids,
                    parameters={
                        "software": software,
                        "task": task,
                        "figure": figure["path"],
                        "status": audit.get("status"),
                    },
                    software=software,
                    metadata={
                        "evidence_key": "visual_qa",
                        "figure": figure["path"],
                        "helper": "audit_figure.py",
                    },
                )
                summary = {
                    "status": audit.get("status"),
                    "checks": audit.get("checks", {}),
                    "warnings": audit.get("warnings", []),
                    "audit_report": _relative_path(project_root, audit_path),
                    "audit_artifact_id": qa_artifact["artifact_id"],
                }
                figure["visual_qa"] = summary
                qa_entries.append({"figure": figure["path"], **summary})
                qa_statuses.append(str(audit.get("status")))
                qa_warnings.extend(audit.get("warnings", []))
                qa_artifacts.append(qa_artifact)

            manifest["visual_qa"] = {
                "status": _aggregate_visual_qa_status(qa_statuses),
                "checks": {
                    "figures_checked": len(qa_entries),
                    "audit_reports": len(qa_entries),
                },
                "warnings": qa_warnings,
                "figures": qa_entries,
            }
        except Exception as exc:
            warning = f"Visual QA helper failed: {exc}"
            manifest["visual_qa"] = {
                "status": "error",
                "checks": {},
                "warnings": [warning],
                "figures": [],
            }
            for figure in manifest["figures"]:
                figure["visual_qa"] = {
                    "status": "error",
                    "checks": {},
                    "warnings": [warning],
                }
    else:
        reason = manifest["skipped_reasons"][-1] if manifest["skipped_reasons"] else "No rendered figures were generated."
        qa_status = "skipped_optional_dependency" if manifest["status"] == "skipped_optional_dependency" else "skipped"
        manifest["visual_qa"] = _visual_qa_skipped(reason, status=qa_status)

    manifest["figure_traceability"]["figures"] = [
        {
            "name": figure["name"],
            "path": figure["path"],
            "source_data": figure.get("source_data"),
            "plotting_script": figure.get("plotting_script"),
            "analysis_report_artifact_id": figure.get("analysis_report_artifact_id"),
            "visual_qa": figure.get("visual_qa"),
        }
        for figure in manifest["figures"]
    ]
    manifest_path = reports_dir / "figures_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    manifest_artifact = register_artifact(
        "figures_manifest.json",
        "figures_manifest",
        "analysis_visualization",
        project_root=str(project_root),
        path=_relative_path(project_root, manifest_path),
        parent_artifacts=[*parent_artifact_ids, *[artifact["artifact_id"] for artifact in qa_artifacts]],
        parameters={"software": software, "task": task, "status": manifest["status"]},
        software=software,
        metadata={"evidence_key": "figure_manifest"},
    )
    figure_artifacts = []
    for figure in manifest["figures"]:
        figure_artifacts.append(register_artifact(
            figure["name"],
            "figure",
            "analysis_visualization",
            project_root=str(project_root),
            path=figure["path"],
            parent_artifacts=[manifest_artifact["artifact_id"], analysis_report_artifact["artifact_id"]],
            parameters={"software": software, "task": task},
            software=software,
            metadata={
                "evidence_key": "figure",
                "source_data": figure.get("source_data"),
                "plotting_script": figure.get("plotting_script"),
                "visual_qa_artifact_id": figure.get("visual_qa", {}).get("audit_artifact_id"),
            },
        ))

    return {
        "status": "success",
        "artifacts": [manifest_artifact, *qa_artifacts, *figure_artifacts],
        "manifest": manifest,
        "inputs": parent_artifact_ids,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the built-in optional visualization stage runner")
    parser.add_argument("--workflow-dir", required=True, help="Path to .simflow directory")
    parser.add_argument("--params", type=str, default="{}", help="JSON parameters for the stage")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--execute", dest="dry_run", action="store_false")
    args = parser.parse_args()

    try:
        params = json.loads(args.params)
        result = run_visualization_stage(args.workflow_dir, params=params, dry_run=args.dry_run)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
