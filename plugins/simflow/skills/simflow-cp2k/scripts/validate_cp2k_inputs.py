#!/usr/bin/env python3
"""Validate common-task CP2K inputs inside a SimFlow project."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from _common import ensure_cp2k_project, finalize_stage, register_report, write_json_verified
from runtime.lib.cp2k_validation import normalize_cp2k_task, validate_cp2k_inputs


def run_validation(
    task: str,
    project_root: str,
    calc_dir: str = ".",
    input_path: str | None = None,
) -> dict:
    """Validate a CP2K input deck and write the SimFlow report output."""
    task_norm = normalize_cp2k_task(task)
    root, state = ensure_cp2k_project(project_root, "input_generation")
    work_dir = (root / calc_dir).resolve()

    if input_path and not input_path.startswith("/"):
        input_path = str(work_dir / input_path)

    report = validate_cp2k_inputs(task_norm, str(work_dir), input_path=input_path)
    handoff = {
        "task": task_norm,
        "validation_status": report["status"],
        "next_steps": [
            "Fix failed checks before any compute preparation." if report["status"] == "fail" else "Validation passed or was skipped for this task.",
            "Use orchestrate_cp2k_task.py for the full dry-run planning/report flow.",
        ],
        "approval_needed": False,
    }
    files = {
        "validation_report": write_json_verified(root, "reports/cp2k/validation_report.json", report),
        "handoff_artifact": write_json_verified(root, "reports/cp2k/handoff_artifact.json", handoff),
    }
    artifacts = [
        register_report(root, "input_generation", task_norm, "validation_report", files["validation_report"]),
        register_report(root, "input_generation", task_norm, "handoff_artifact", files["handoff_artifact"], artifact_type="handoff"),
    ]
    checkpoint = finalize_stage(
        root,
        state,
        "input_generation",
        task_norm,
        files,
        "success" if report["status"] in {"pass", "skip"} else "failed",
        f"Validated CP2K inputs for {task_norm}.",
    )
    return {
        "status": "success",
        "task": task_norm,
        "validation_report": report,
        "reports": files,
        "artifacts": artifacts,
        "checkpoint": checkpoint,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate common-task CP2K inputs inside a SimFlow project")
    parser.add_argument("--task", required=True, help="CP2K task or workflow mode")
    parser.add_argument("--project-root", required=True, help="User project root for .simflow and reports")
    parser.add_argument("--calc-dir", default=".", help="Calculation directory relative to project_root")
    parser.add_argument("--input-path", help="Input deck path, relative to calc-dir unless absolute")
    args = parser.parse_args()

    try:
        result = run_validation(
            task=args.task,
            project_root=args.project_root,
            calc_dir=args.calc_dir,
            input_path=args.input_path,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, indent=2, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
