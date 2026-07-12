#!/usr/bin/env python3
"""Orchestrate GPUMD/NEP helper reports without submitting jobs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from runtime.simflow_core.result_contract import attach_simflow_result
from runtime.simflow_core.script_contracts import add_helper_recording_args, maybe_record_helper_run
from runtime.simflow_core.state import resolve_project_path, resolve_project_root
from runtime.simflow_helpers.engines.gpumd import build_gpumd_task_plan, normalize_gpumd_task, read_extxyz_summary


def _write_json(root: Path, relative_path: str, data: dict[str, Any]) -> str:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    json.loads(path.read_text(encoding="utf-8"))
    return relative_path


def _has_outputs(work_dir: Path) -> bool:
    return any((work_dir / name).is_file() for name in ("thermo.out", "loss.out", "energy_train.out", "force_train.out"))


def _analysis_report(work_dir: Path, task: str) -> dict[str, Any]:
    if not _has_outputs(work_dir):
        return {
            "status": "missing_outputs",
            "message": "No GPUMD/NEP outputs were detected in the calculation directory.",
            "files": [],
        }
    files = []
    for name in ("thermo.out", "loss.out", "energy_train.out", "energy_test.out", "force_train.out", "force_test.out"):
        path = work_dir / name
        if path.is_file():
            files.append({"path": str(path), "bytes": path.stat().st_size})
    return {
        "status": "available_for_parsing",
        "task": task,
        "files": files,
        "message": "Use parse_gpumd_outputs.py for conservative table summaries.",
    }


def _orchestration_outcome(task: str, validation_status: str | None) -> dict[str, str]:
    status = str(validation_status or "").strip().lower()
    if task == "unknown" or status in {"skip", "skipped"}:
        return {
            "result_status": "needs_clarification",
            "stage_status": "in_progress",
            "checkpoint_status": "partial",
            "message": "GPUMD/NEP task intent requires clarification before computation can proceed.",
        }
    if status == "warning":
        return {
            "result_status": "warning",
            "stage_status": "in_progress",
            "checkpoint_status": "partial",
            "message": "GPUMD/NEP dry-run planning completed with validation warnings.",
        }
    if status in {"pass", "success"}:
        return {
            "result_status": "success",
            "stage_status": "in_progress",
            "checkpoint_status": "partial",
            "message": "GPUMD/NEP dry-run planning completed; no computation was executed.",
        }
    return {
        "result_status": "blocked",
        "stage_status": "failed",
        "checkpoint_status": "failure",
        "message": "GPUMD/NEP input validation failed; computation remains blocked.",
    }


def orchestrate_gpumd_task(
    task: str,
    project_root: str,
    calc_dir: str = ".",
    options: dict | None = None,
) -> dict:
    """Build GPUMD/NEP evidence reports without mutating workflow state."""
    options = dict(options or {})
    software = options.get("software", "gpumd")
    try:
        task_norm = normalize_gpumd_task(task, software=software)
    except ValueError:
        task_norm = "unknown"
    stage = "analysis_visualization" if task_norm in {"parse", "troubleshoot"} else "computation"
    root = resolve_project_root(project_root=project_root)
    work_dir = resolve_project_path(calc_dir, project_root=str(root))
    work_dir.mkdir(parents=True, exist_ok=True)

    if task_norm == "unknown":
        manifest = {
            "task": "unknown",
            "calc_dir": str(work_dir),
            "classification_status": "needs_clarification",
            "candidates": ["gpumd_minimize", "gpumd_md_nve", "gpumd_md_nvt", "gpumd_md_npt", "nep_training", "nep_prediction", "parse"],
            "missing_information": ["GPUMD/NEP task intent"],
        }
        validation = {"status": "skip", "checks": [], "reason": "No fixed GPUMD/NEP validator selected for an unknown task."}
        compute_plan = {"software": software, "task": "unknown", "dry_run": True, "real_submit_allowed": False}
    else:
        plan = build_gpumd_task_plan(task_norm, str(root), {**options, "calc_dir": calc_dir, "software": software})
        manifest = {
            "task": plan["task"],
            "calc_dir": str(work_dir),
            "classification_status": "classified",
            "expected_artifacts": plan["expected_artifacts"],
            "model_xyz": read_extxyz_summary(work_dir / "model.xyz") if (work_dir / "model.xyz").exists() else None,
            "train_xyz": read_extxyz_summary(work_dir / "train.xyz") if (work_dir / "train.xyz").exists() else None,
        }
        validation = plan["validation_report"]
        compute_plan = plan["compute_plan"]

    analysis = _analysis_report(work_dir, task_norm)
    outcome = _orchestration_outcome(task_norm, validation.get("status"))
    handoff = {
        "status": outcome["result_status"],
        "task": task_norm,
        "reports": [
            "reports/gpumd/input_manifest.json",
            "reports/gpumd/validation_report.json",
            "reports/gpumd/compute_plan.json",
            "reports/gpumd/analysis_report.json",
        ],
        "validation_status": validation.get("status"),
        "analysis_status": analysis.get("status"),
        "stage_status": outcome["stage_status"],
        "approval_needed": True,
        "real_submit_allowed": False,
        "next_steps": [
            "Review validation_report.json and compute_plan.json.",
            "Record hpc_submit approval evidence before any real local, remote, or HPC execution.",
        ],
    }
    files = {
        "input_manifest": _write_json(root, "reports/gpumd/input_manifest.json", manifest),
        "validation_report": _write_json(root, "reports/gpumd/validation_report.json", validation),
        "compute_plan": _write_json(root, "reports/gpumd/compute_plan.json", compute_plan),
        "analysis_report": _write_json(root, "reports/gpumd/analysis_report.json", analysis),
        "handoff_artifact": _write_json(root, "reports/gpumd/handoff_artifact.json", handoff),
    }
    result = {
        "status": outcome["result_status"],
        "task": task_norm,
        "reports": files,
        "stage_status": outcome["stage_status"],
        "checkpoint_status": outcome["checkpoint_status"],
        "message": outcome["message"],
    }
    reason_code = "needs_clarification" if task_norm == "unknown" else f"validation_{validation.get('status', 'unknown')}"
    return attach_simflow_result(
        result,
        role="helper",
        activity="orchestration",
        legacy_status=result["status"],
        stage=stage,
        reason_code=reason_code,
        state_effect="none",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Orchestrate GPUMD/NEP tasks without submitting jobs")
    parser.add_argument("--task", required=True)
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--calc-dir", default=".")
    parser.add_argument("--options", default="{}")
    add_helper_recording_args(parser, default_stage="computation")
    args = parser.parse_args()

    try:
        result = orchestrate_gpumd_task(args.task, args.project_root, args.calc_dir, json.loads(args.options))
        result = maybe_record_helper_run(
            args=args,
            result=result,
            script_path=Path(__file__).resolve(),
            helper_name="gpumd_orchestrate_task",
            software=result.get("task", "gpumd"),
            output_paths=list(result.get("reports", {}).values()),
        )
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, indent=2, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
