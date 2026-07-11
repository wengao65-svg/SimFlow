#!/usr/bin/env python3
"""Orchestrate common VASP tasks inside SimFlow.

By default this script writes report files under reports/vasp/. It touches
.simflow only when explicit helper-run recording is requested, and it never
submits HPC jobs.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SIMFLOW_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SIMFLOW_ROOT))

from runtime.simflow_core.result_contract import attach_simflow_result
from runtime.simflow_core.script_contracts import add_helper_recording_args, maybe_record_helper_run
from runtime.simflow_core.state import resolve_project_root
from runtime.simflow_helpers.engines.vasp_workflows import build_vasp_task_plan, suggest_vasp_stage, write_vasp_artifacts


def orchestrate_vasp_task(
    task: str,
    base_dir: str,
    calc_dir: str = ".",
    options: dict | None = None,
) -> dict:
    """Build VASP orchestration evidence reports without mutating workflow state."""
    options = dict(options or {})
    options["calc_dir"] = calc_dir
    project_root = resolve_project_root(project_root=base_dir)

    plan = build_vasp_task_plan(task, str(project_root), options)
    written = write_vasp_artifacts(plan, str(project_root))
    result = {"status": "success", "plan": plan, "written": written}
    return attach_simflow_result(
        result,
        role="helper",
        activity="orchestration",
        legacy_status=result["status"],
        stage=plan.get("stage") or suggest_vasp_stage(plan["task"]),
        state_effect="none",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Write reports/vasp VASP helper reports without submitting jobs; "
            ".simflow is touched only by explicit helper-run recording"
        )
    )
    parser.add_argument("--task", required=True, help="Task request or task name")
    parser.add_argument("--base-dir", default=".", help="Project root for default reports/vasp output")
    parser.add_argument(
        "--project-root",
        help="Project root for reports/vasp output and optional explicit helper-run recording",
    )
    parser.add_argument("--calc-dir", default=".", help="Calculation directory relative to base-dir")
    parser.add_argument("--options", default="{}", help="JSON options")
    add_helper_recording_args(parser, default_stage="computation")
    args = parser.parse_args()

    try:
        if args.project_root is None:
            args.project_root = args.base_dir
        result = orchestrate_vasp_task(
            task=args.task,
            base_dir=args.project_root,
            calc_dir=args.calc_dir,
            options=json.loads(args.options),
        )
        result = maybe_record_helper_run(
            args=args,
            result=result,
            script_path=Path(__file__).resolve(),
            helper_name="vasp_orchestrate_task",
            software="vasp",
            output_paths=list(result.get("written", {}).get("files", {}).values()),
            sensitive_json_cli_options={"--options": []},
        )
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
