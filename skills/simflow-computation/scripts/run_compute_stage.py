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

from runtime.simflow_core.artifacts import get_artifact, list_artifacts, register_artifact
from runtime.simflow_core.proposals import load_proposal_contract
from runtime.simflow_core.state import read_state
from runtime.simflow_helpers.computation.readiness import build_computation_readiness, write_readiness_evidence
from runtime.simflow_helpers.engines.cp2k import build_cp2k_task_plan
from runtime.simflow_helpers.engines.vasp import build_vasp_task_plan


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
    "skills/simflow-computation/scripts/prepare_job.py",
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
    if not artifacts:
        artifacts = list_artifacts(stage=stage_name, project_root=str(project_root))
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
    if software == "lammps":
        input_name = next(
            (Path(path).name for path in input_manifest.get("generated_files", []) if Path(path).name.startswith("in.")),
            "in.lammps",
        )
        return f"lmp -in {input_name}"
    task = input_manifest.get("task", "scf")
    return "vasp_gam" if task in {"scf", "static"} else "vasp_std"


def _recommended_command(software: str, script_name: str, raw_plan: dict[str, Any], executable: str) -> str:
    if software == "cp2k":
        return raw_plan["compute_plan"].get("recommended_command", f"{executable} -i <input.inp> -o cp2k.log")
    if software == "lammps":
        return raw_plan["compute_plan"].get("recommended_command", executable)
    return f"{executable} > vasp.out"


def _build_lammps_task_plan(task: str, input_manifest: dict[str, Any]) -> dict[str, Any]:
    num_atoms = int(input_manifest.get("num_atoms") or 50)
    task_class = "minimize" if task == "minimize" else "production"
    resources = {
        "estimated_walltime_hours": 1 if task_class == "minimize" else 2,
        "recommended_nodes": 1,
        "recommended_ntasks": min(64, max(1, (num_atoms // 1000) + 1) * 16),
        "recommended_memory_gb": max(4, min(256, num_atoms // 250 + 4)),
    }
    input_name = next(
        (Path(path).name for path in input_manifest.get("generated_files", []) if Path(path).name.startswith("in.")),
        "in.lammps",
    )
    return {
        "compute_plan": {
            "resources": resources,
            "recommended_command": f"lmp -in {input_name}",
            "hpc_submit_gate": "approval_required",
        },
        "validation_report": {
            "status": "warning" if input_manifest.get("warnings") else "pass",
            "warnings": input_manifest.get("warnings", []),
        },
    }


def _failed_readiness_checks(readiness: dict[str, Any]) -> list[str]:
    checks = {
        "input_validation": readiness["input_validation"]["status"],
        "resource_estimate": readiness["resource_estimate"]["status"],
        "credential_scan": readiness["credential_scan"]["status"],
    }
    return [name for name, status in checks.items() if status == "fail"]


def _build_user_submit_readiness(readiness: dict[str, Any], evidence_paths: dict[str, str]) -> dict[str, Any]:
    failed_checks = _failed_readiness_checks(readiness)
    ready_for_approval = readiness["status"] in {"pass", "warning"} and not failed_checks
    next_actions = [
        "Review dry-run evidence, input validation, resource estimate, credential scan, and job script hash.",
    ]
    if ready_for_approval:
        next_actions.append("Record an explicit hpc_submit gate approval before any real local, remote, or HPC submit.")
    else:
        next_actions.append("Fix failed readiness checks before requesting submit approval.")

    return {
        "status": readiness["status"],
        "ready_for_approval": ready_for_approval,
        "real_submit_allowed": False,
        "approval_required": True,
        "failed_checks": failed_checks,
        "evidence": {
            "calculation_manifest": evidence_paths["calculation_manifest"],
            "input_validation": evidence_paths["input_validation"],
            "resource_estimate": evidence_paths["resource_estimate"],
            "credential_scan": evidence_paths["credential_scan"],
            "dry_run_report": evidence_paths["dry_run_report"],
        },
        "hashes": {
            "job_script_hash": readiness["dry_run_report"]["script_hash"],
            "input_manifest_hash": readiness["dry_run_report"]["input_manifest_hash"],
        },
        "next_actions": next_actions,
    }


def _render_submit_readiness_summary(summary: dict[str, Any]) -> str:
    failed = summary["failed_checks"] or ["none"]
    evidence = summary["evidence"]
    hashes = summary["hashes"]
    return "\n".join([
        "# Submit Readiness Summary",
        "",
        f"- Status: {summary['status']}",
        f"- Ready for approval: {summary['ready_for_approval']}",
        f"- Real submit allowed: {summary['real_submit_allowed']}",
        f"- Approval required: {summary['approval_required']}",
        "",
        "## Evidence",
        *(f"- {key}: {value}" for key, value in evidence.items()),
        "",
        "## Hashes",
        f"- Job script hash: {hashes['job_script_hash']}",
        f"- Input manifest hash: {hashes['input_manifest_hash']}",
        "",
        "## Failed Checks",
        *(f"- {item}" for item in failed),
        "",
        "## Next Actions",
        *(f"- {item}" for item in summary["next_actions"]),
        "",
    ])


def run_compute_stage(workflow_dir: str, params: dict | None = None, dry_run: bool = False) -> dict:
    project_root = resolve_project_root_from_workflow_dir(workflow_dir)
    state = read_state(project_root=str(project_root), state_file="workflow.json")
    if not state:
        return {"status": "error", "message": "No workflow state found"}

    params = params or {}
    contract = load_proposal_contract(str(project_root / ".simflow"), allow_direct_entry=True)
    input_artifacts = _stage_output_artifacts(project_root, "computation")
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
    elif software == "lammps":
        raw_plan = _build_lammps_task_plan(task, input_manifest)
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
    readiness = build_computation_readiness(
        project_root=project_root,
        software=software,
        task=task,
        scheduler=scheduler,
        input_manifest=input_manifest,
        input_manifest_path=input_manifest_path,
        job_script_path=staged_script_path,
        resource_estimate=resources,
        compute_plan=compute_plan,
    )
    evidence_paths = write_readiness_evidence(project_root, readiness)
    compute_plan["submit_readiness"] = readiness["submit_readiness"]
    compute_plan["evidence_paths"] = evidence_paths
    compute_plan["readiness_status"] = readiness["status"]
    compute_plan["user_submit_readiness"] = _build_user_submit_readiness(readiness, evidence_paths)
    dry_run_report = readiness["dry_run_report"]

    compute_plan_path = reports_dir / "compute_plan.json"
    dry_run_report_path = reports_dir / "dry_run_report.json"
    submit_readiness_summary_path = reports_dir / "submit_readiness_summary.md"
    compute_plan_path.write_text(json.dumps(compute_plan, indent=2, ensure_ascii=False), encoding="utf-8")
    dry_run_report_path.write_text(json.dumps(dry_run_report, indent=2, ensure_ascii=False), encoding="utf-8")
    submit_readiness_summary_path.write_text(
        _render_submit_readiness_summary(compute_plan["user_submit_readiness"]),
        encoding="utf-8",
    )

    if dry_run:
        return {
            "status": "dry_run_complete",
            "manifest": compute_plan,
            "inputs": parent_artifact_ids,
            "planned_outputs": [
                ".simflow/reports/compute/compute_plan.json",
                ".simflow/reports/compute/dry_run_report.json",
                ".simflow/reports/compute/submit_readiness_summary.md",
                ".simflow/artifacts/compute/calculation_manifest.json",
                ".simflow/artifacts/compute/input_validation.json",
                ".simflow/artifacts/compute/resource_estimate.json",
                ".simflow/artifacts/compute/dry_run_report.json",
                ".simflow/artifacts/security/credential_scan.json",
                f".simflow/artifacts/compute/{staged_script_path.name}",
            ],
        }

    compute_plan_artifact = register_artifact(
        "compute_plan.json",
        "compute_plan",
        "computation",
        project_root=str(project_root),
        path=_relative_path(project_root, compute_plan_path),
        parent_artifacts=parent_artifact_ids,
        parameters={"software": software, "task": task, "scheduler": scheduler},
        software=software,
        metadata={"evidence_keys": ["calculation_manifest", "compute_plan"]},
    )
    job_script_artifact = register_artifact(
        staged_script_path.name,
        "job_script",
        "computation",
        project_root=str(project_root),
        path=_relative_path(project_root, staged_script_path),
        parent_artifacts=[compute_plan_artifact["artifact_id"]],
        parameters={"software": software, "task": task, "scheduler": scheduler},
        software=software,
        metadata={"evidence_keys": ["job_script"]},
    )
    calculation_manifest_artifact = register_artifact(
        "calculation_manifest.json",
        "calculation_manifest",
        "computation",
        project_root=str(project_root),
        path=evidence_paths["calculation_manifest"],
        parent_artifacts=[compute_plan_artifact["artifact_id"], job_script_artifact["artifact_id"]],
        parameters={"software": software, "task": task, "scheduler": scheduler},
        software=software,
        metadata={"evidence_keys": ["calculation_manifest"]},
    )
    input_validation_artifact = register_artifact(
        "input_validation.json",
        "input_validation_report",
        "computation",
        project_root=str(project_root),
        path=evidence_paths["input_validation"],
        parent_artifacts=[calculation_manifest_artifact["artifact_id"], input_manifest_artifact["artifact_id"]],
        parameters={"software": software, "task": task, "scheduler": scheduler},
        software=software,
        metadata={"evidence_keys": ["input_validation_report"]},
    )
    resource_estimate_artifact = register_artifact(
        "resource_estimate.json",
        "resource_estimate",
        "computation",
        project_root=str(project_root),
        path=evidence_paths["resource_estimate"],
        parent_artifacts=[calculation_manifest_artifact["artifact_id"]],
        parameters={"software": software, "task": task, "scheduler": scheduler},
        software=software,
        metadata={"evidence_keys": ["resource_estimate"]},
    )
    credential_scan_artifact = register_artifact(
        "credential_scan.json",
        "credential_scan",
        "computation",
        project_root=str(project_root),
        path=evidence_paths["credential_scan"],
        parent_artifacts=[calculation_manifest_artifact["artifact_id"]],
        parameters={"software": software, "task": task, "scheduler": scheduler},
        software=software,
        metadata={"evidence_keys": ["credential_scan"]},
    )
    dry_run_artifact = register_artifact(
        "dry_run_report.json",
        "dry_run_report",
        "computation",
        project_root=str(project_root),
        path=evidence_paths["dry_run_report"],
        parent_artifacts=[
            calculation_manifest_artifact["artifact_id"],
            input_validation_artifact["artifact_id"],
            resource_estimate_artifact["artifact_id"],
            credential_scan_artifact["artifact_id"],
        ],
        parameters={"software": software, "task": task, "scheduler": scheduler},
        software=software,
        metadata={"evidence_keys": ["dry_run_report"]},
    )
    submit_readiness_artifact = register_artifact(
        "submit_readiness_summary.md",
        "submit_readiness_summary",
        "computation",
        project_root=str(project_root),
        path=_relative_path(project_root, submit_readiness_summary_path),
        parent_artifacts=[dry_run_artifact["artifact_id"]],
        parameters={
            "readiness_status": readiness["status"],
            "ready_for_approval": compute_plan["user_submit_readiness"]["ready_for_approval"],
            "real_submit_allowed": False,
        },
        software=software,
        metadata={"evidence_key": "submit_readiness"},
    )

    return {
        "status": "success",
        "artifacts": [
            compute_plan_artifact,
            job_script_artifact,
            calculation_manifest_artifact,
            input_validation_artifact,
            resource_estimate_artifact,
            credential_scan_artifact,
            dry_run_artifact,
            submit_readiness_artifact,
        ],
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
