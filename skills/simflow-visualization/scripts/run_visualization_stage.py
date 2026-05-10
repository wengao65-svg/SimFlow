#!/usr/bin/env python3
"""Run the canonical visualization stage for Milestone C."""

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


def run_visualization_stage(workflow_dir: str, params: dict | None = None, dry_run: bool = False) -> dict:
    project_root = resolve_project_root_from_workflow_dir(workflow_dir)
    state = read_state(project_root=str(project_root), state_file="workflow.json")
    if not state:
        return {"status": "error", "message": "No workflow state found"}

    contract = load_proposal_contract(str(project_root / ".simflow"))
    analysis_artifacts = _stage_output_artifacts(project_root, "analysis")
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
        "figures": [],
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
            "skills/simflow-visualization/scripts/plot_energy_curve.py",
            "parse_energies",
            "simflow_parse_energies",
        )
        plot_energy_curve = _load_function(
            "skills/simflow-visualization/scripts/plot_energy_curve.py",
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
                    })
        else:
            return {"status": "error", "message": f"Unsupported software for visualization stage: {software}"}

    manifest_path = reports_dir / "figures_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    manifest_artifact = register_artifact(
        "figures_manifest.json",
        "figures_manifest",
        "visualization",
        project_root=str(project_root),
        path=_relative_path(project_root, manifest_path),
        parent_artifacts=parent_artifact_ids,
        parameters={"software": software, "task": task, "status": manifest["status"]},
        software=software,
    )
    figure_artifacts = []
    for figure in manifest["figures"]:
        figure_artifacts.append(register_artifact(
            figure["name"],
            "figure",
            "visualization",
            project_root=str(project_root),
            path=figure["path"],
            parent_artifacts=[manifest_artifact["artifact_id"]],
            parameters={"software": software, "task": task},
            software=software,
        ))

    return {
        "status": "success",
        "artifacts": [manifest_artifact, *figure_artifacts],
        "manifest": manifest,
        "inputs": parent_artifact_ids,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the canonical visualization stage")
    parser.add_argument("--workflow-dir", required=True, help="Path to .simflow directory")
    parser.add_argument("--params", type=str, default="{}", help="JSON parameters for the stage")
    parser.add_argument("--dry-run", action="store_true", default=False)
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
