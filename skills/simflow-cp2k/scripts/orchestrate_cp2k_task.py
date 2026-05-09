#!/usr/bin/env python3
"""Orchestrate common CP2K tasks inside a SimFlow project."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from _common import ensure_cp2k_project, finalize_stage, register_report, write_json_verified
from runtime.lib.cp2k_validation import normalize_cp2k_task
from runtime.lib.cp2k_workflows import build_cp2k_task_plan
from runtime.lib.parsers.cp2k_parser import CP2KParser


def orchestrate_cp2k_task(
    task: str,
    project_root: str,
    calc_dir: str = ".",
    options: dict | None = None,
) -> dict:
    """Build CP2K reports, artifacts, checkpoint, and handoff without submitting jobs."""
    options = dict(options or {})
    options["calc_dir"] = calc_dir
    task_norm = normalize_cp2k_task(task)
    stage = "analysis" if task_norm in {"parse", "troubleshoot"} else "input_generation"
    root, state = ensure_cp2k_project(project_root, stage)
    work_dir = (root / calc_dir).resolve()
    work_dir.mkdir(parents=True, exist_ok=True)

    plan = build_cp2k_task_plan(task_norm, str(root), options)
    parser = CP2KParser()
    analysis = parser.parse_outputs(str(work_dir), project=options.get("project")) if _has_outputs(work_dir) else {
        "status": "missing_outputs",
        "files": {"log": None, "ener": None, "trajectory": None, "restart": None},
        "summary": {},
        "message": "No CP2K outputs were detected in the calculation directory.",
    }

    manifest = {
        "task": plan["task"],
        "calc_dir": str(work_dir),
        "required_inputs": plan["classification"]["required_inputs"],
        "available_inputs": plan["classification"]["available_inputs"],
        "missing_inputs": plan["classification"]["missing_inputs"],
        "recommended_tools": plan["classification"]["recommended_tools"],
        "file_inventory": plan["classification"]["file_inventory"],
        "expected_artifacts": plan["expected_artifacts"],
    }
    handoff = {
        "task": plan["task"],
        "reports": plan["expected_artifacts"],
        "validation_status": plan["validation_report"]["status"],
        "analysis_status": analysis["status"],
        "next_steps": _next_steps(plan["validation_report"]["status"], analysis["status"]),
        "approval_needed": True,
        "real_submit_allowed": False,
    }

    files = {
        "input_manifest": write_json_verified(root, "reports/cp2k/input_manifest.json", manifest),
        "validation_report": write_json_verified(root, "reports/cp2k/validation_report.json", plan["validation_report"]),
        "compute_plan": write_json_verified(root, "reports/cp2k/compute_plan.json", plan["compute_plan"]),
        "analysis_report": write_json_verified(root, "reports/cp2k/analysis_report.json", analysis),
        "handoff_artifact": write_json_verified(root, "reports/cp2k/handoff_artifact.json", handoff),
    }

    artifacts = []
    for name, rel_path in files.items():
        artifacts.append(register_report(
            root,
            stage,
            plan["task"],
            name,
            rel_path,
            artifact_type="handoff" if name == "handoff_artifact" else "report",
        ))

    checkpoint = finalize_stage(
        root,
        state,
        stage,
        plan["task"],
        files,
        "success" if plan["validation_report"]["status"] in {"pass", "skip"} else "failed",
        f"CP2K {plan['task']} orchestration reports written.",
    )
    return {
        "status": "success",
        "task": plan["task"],
        "plan": plan,
        "analysis_report": analysis,
        "reports": files,
        "artifacts": artifacts,
        "checkpoint": checkpoint,
    }


def _has_outputs(work_dir: Path) -> bool:
    patterns = ("*.log", "*.ener", "*-pos-*.xyz", "*.restart")
    return any(any(work_dir.glob(pattern)) for pattern in patterns)


def _next_steps(validation_status: str, analysis_status: str) -> list[str]:
    steps = []
    if validation_status == "fail":
        steps.append("Fix failed validation checks before any CP2K execution or continuation.")
    else:
        steps.append("Validation is ready for dry-run compute preparation.")
    if analysis_status == "missing_outputs":
        steps.append("Run CP2K later with approval or provide existing outputs for parsing.")
    else:
        steps.append("Review parsed convergence, energy, temperature, and restart summary.")
    steps.append("Any real HPC submission still requires the approval gate.")
    return steps


def main() -> None:
    parser = argparse.ArgumentParser(description="Orchestrate common CP2K tasks without submitting jobs")
    parser.add_argument("--task", required=True, help="CP2K task or workflow mode")
    parser.add_argument("--project-root", required=True, help="User project root for .simflow and reports")
    parser.add_argument("--calc-dir", default=".", help="Calculation directory relative to project_root")
    parser.add_argument("--options", default="{}", help="JSON options")
    args = parser.parse_args()

    try:
        result = orchestrate_cp2k_task(
            task=args.task,
            project_root=args.project_root,
            calc_dir=args.calc_dir,
            options=json.loads(args.options),
        )
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, indent=2, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
