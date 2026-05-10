#!/usr/bin/env python3
"""Run the canonical compute stage for Milestone C."""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from runtime.lib.artifact import get_artifact, register_artifact
from runtime.lib.cp2k_workflows import build_cp2k_task_plan
from runtime.lib.proposal_contract import load_proposal_contract
from runtime.lib.state import read_state
from runtime.lib.vasp_workflows import build_vasp_task_plan


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


PREPARE_JOB = _load_function(
    "skills/simflow-compute/scripts/prepare_job.py",
    "prepare_job",
    "simflow_prepare_job",
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


def _walltime(hours: float) -> str:
    total_minutes = max(60, int(round(hours * 60)))
    hh, mm = divmod(total_minutes, 60)
    return f"{hh:02d}:{mm:02d}:00"


def _script_name_for_scheduler(scheduler: str) -> str:
    return "job_script.pbs" if scheduler == "pbs" else "job_script.sh"


def _recommended_executable(software: str, input_manifest: dict[str, Any], raw_plan: dict[str, Any]) -> str:
    if software == "cp2k":
        runtime_detection = raw_plan["compute_plan"].get("runtime_detection", {})
        executables = runtime_detection.get("executables", [])
        if executables:
            return executables[0]["executable"]
        return "cp2k.psmp"
    task = input_manifest.get("task", "scf")
    return "vasp_gam" if task in {"scf", "static"} else "vasp_std"


def _recommended_command(software: str, script_name: str, raw_plan: dict[str, Any], executable: str) -> str:
    if software == "cp2k":
        return raw_plan["compute_plan"].get("recommended_command", f"{executable} -i <input.inp> -o cp2k.log")
    return f"{executable} > vasp.out"


def run_compute_stage(workflow_dir: str, params: dict | None = None, dry_run: bool = False) -> dict:
    project_root = resolve_project_root_from_workflow_dir(workflow_dir)
    state = read_state(project_root=str(project_root), state_file="workflow.json")
    if not state:
        return {"status": "error", "message": "No workflow state found"}

    params = params or {}
    contract = load_proposal_contract(str(project_root / ".simflow"))
    input_artifacts = _stage_output_artifacts(project_root, "input_generation")
    if not input_artifacts:
        return {"status": "error", "message": "Input generation stage has no registered outputs"}

    input_manifest_artifact = next((artifact for artifact in input_artifacts if artifact.get("type") == "input_manifest"), None)
    if not input_manifest_artifact:
        return {"status": "error", "message": "Input generation manifest is missing"}

    input_manifest_path = project_root / input_manifest_artifact["path"]
    input_manifest = json.loads(input_manifest_path.read_text(encoding="utf-8"))
    software = contract["software"]
    task = input_manifest["task"]
    calc_dir = project_root / input_manifest["artifact_dir"]
    parent_artifact_ids = [artifact["artifact_id"] for artifact in input_artifacts]

    reports_dir = project_root / ".simflow" / "reports" / "compute"
    artifacts_dir = project_root / ".simflow" / "artifacts" / "compute"
    reports_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    if software == "vasp":
        mesh = input_manifest.get("kpoints_mesh") or [1, 1, 1]
        num_kpoints = 1
        for value in mesh:
            num_kpoints *= int(value)
        raw_plan = build_vasp_task_plan(
            task,
            str(project_root),
            {
                "calc_dir": input_manifest["artifact_dir"],
                "task": task,
                "num_atoms": input_manifest.get("num_atoms", 1),
                "num_kpoints": num_kpoints,
            },
        )
    elif software == "cp2k":
        raw_plan = build_cp2k_task_plan(
            task,
            str(project_root),
            {
                "calc_dir": input_manifest["artifact_dir"],
                "task": task,
                "input_path": next(
                    (Path(path).name for path in input_manifest.get("generated_files", []) if path.endswith(".inp")),
                    None,
                ),
            },
        )
    else:
        return {"status": "error", "message": f"Unsupported software for compute stage: {software}"}

    scheduler = params.get("scheduler") or input_manifest.get("downstream_compute_hints", {}).get("recommended_scheduler") or "slurm"
    executable = _recommended_executable(software, input_manifest, raw_plan)
    resources = raw_plan["compute_plan"]["resources"]
    config = {
        "software": software,
        "job_type": task,
        "job_name": params.get("job_name", f"simflow-{software}-{task}"),
        "executable": executable,
        "nodes": resources["recommended_nodes"],
        "ntasks": resources["recommended_ntasks"],
        "ppn": resources["recommended_ntasks"],
        "mem": f"{resources['recommended_memory_gb']}GB",
        "time": _walltime(resources["estimated_walltime_hours"]),
        "walltime": _walltime(resources["estimated_walltime_hours"]),
        "partition": params.get("partition", "normal"),
        "queue": params.get("queue", "default"),
        "account": params.get("account"),
        "output": "job.out",
        "error": "job.err",
        "modules": params.get("modules"),
        "pre_commands": params.get("pre_commands"),
        "mpi_launcher": params.get("mpi_launcher", "mpirun"),
    }
    prepared = PREPARE_JOB(config, scheduler, str(artifacts_dir), dry_run=True)
    staged_script_path = artifacts_dir / _script_name_for_scheduler(scheduler)
    shutil.move(prepared["script_path"], staged_script_path)

    compute_plan = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "software": software,
        "task": task,
        "dry_run": True,
        "real_submit": False,
        "approval_required_for_real_submit": True,
        "scheduler": scheduler,
        "input_manifest_artifact_id": input_manifest_artifact["artifact_id"],
        "input_files": input_manifest.get("generated_files", []),
        "resource_estimate": resources,
        "recommended_command": _recommended_command(software, staged_script_path.name, raw_plan, executable),
        "job_script": _relative_path(project_root, staged_script_path),
        "gate_status": raw_plan["compute_plan"].get("hpc_submit_gate"),
        "validation_report": raw_plan.get("validation_report"),
    }
    dry_run_report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "ready_for_approval" if compute_plan["gate_status"] else "planned",
        "software": software,
        "task": task,
        "scheduler": scheduler,
        "job_script": compute_plan["job_script"],
        "recommended_command": compute_plan["recommended_command"],
        "resource_estimate": resources,
        "missing_inputs": raw_plan.get("classification", {}).get("missing_inputs", []),
        "approval_required": True,
    }

    compute_plan_path = reports_dir / "compute_plan.json"
    dry_run_report_path = reports_dir / "dry_run_report.json"
    compute_plan_path.write_text(json.dumps(compute_plan, indent=2, ensure_ascii=False), encoding="utf-8")
    dry_run_report_path.write_text(json.dumps(dry_run_report, indent=2, ensure_ascii=False), encoding="utf-8")

    if dry_run:
        return {
            "status": "dry_run_complete",
            "manifest": compute_plan,
            "inputs": parent_artifact_ids,
            "planned_outputs": [
                ".simflow/reports/compute/compute_plan.json",
                ".simflow/reports/compute/dry_run_report.json",
                f".simflow/artifacts/compute/{staged_script_path.name}",
            ],
        }

    compute_plan_artifact = register_artifact(
        "compute_plan.json",
        "compute_plan",
        "compute",
        project_root=str(project_root),
        path=_relative_path(project_root, compute_plan_path),
        parent_artifacts=parent_artifact_ids,
        parameters={"software": software, "task": task, "scheduler": scheduler},
        software=software,
    )
    job_script_artifact = register_artifact(
        staged_script_path.name,
        "job_script",
        "compute",
        project_root=str(project_root),
        path=_relative_path(project_root, staged_script_path),
        parent_artifacts=[compute_plan_artifact["artifact_id"]],
        parameters={"software": software, "task": task, "scheduler": scheduler},
        software=software,
    )
    dry_run_artifact = register_artifact(
        "dry_run_report.json",
        "dry_run_report",
        "compute",
        project_root=str(project_root),
        path=_relative_path(project_root, dry_run_report_path),
        parent_artifacts=[compute_plan_artifact["artifact_id"]],
        parameters={"software": software, "task": task, "scheduler": scheduler},
        software=software,
    )

    return {
        "status": "success",
        "artifacts": [compute_plan_artifact, job_script_artifact, dry_run_artifact],
        "manifest": compute_plan,
        "inputs": parent_artifact_ids,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the canonical compute stage")
    parser.add_argument("--workflow-dir", required=True, help="Path to .simflow directory")
    parser.add_argument("--params", type=str, default="{}", help="JSON parameters for the stage")
    parser.add_argument("--dry-run", action="store_true", default=False)
    args = parser.parse_args()

    try:
        params = json.loads(args.params)
        result = run_compute_stage(args.workflow_dir, params=params, dry_run=args.dry_run)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
