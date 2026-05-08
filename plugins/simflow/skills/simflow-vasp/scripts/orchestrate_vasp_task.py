#!/usr/bin/env python3
"""Orchestrate common VASP tasks inside SimFlow.

This script writes reports and SimFlow state only. It never submits HPC jobs.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SIMFLOW_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SIMFLOW_ROOT))

from runtime.lib.state import ensure_workflow_initialized, resolve_project_root
from runtime.lib.vasp_workflows import build_vasp_task_plan, write_vasp_artifacts


def orchestrate_vasp_task(
    task: str,
    base_dir: str,
    calc_dir: str = ".",
    options: dict | None = None,
) -> dict:
    """Build VASP orchestration reports, artifacts, and checkpoint."""
    options = dict(options or {})
    options["calc_dir"] = calc_dir
    project_root = resolve_project_root(project_root=base_dir)
    state = ensure_workflow_initialized("dft", "input_generation", project_root=str(project_root))

    plan = build_vasp_task_plan(task, str(project_root), options)
    written = write_vasp_artifacts(plan, str(project_root), workflow_id=state.get("workflow_id"))
    return {"status": "success", "plan": plan, "written": written}


def main() -> None:
    parser = argparse.ArgumentParser(description="Orchestrate common VASP tasks without submitting jobs")
    parser.add_argument("--task", required=True, help="Task request or task name")
    parser.add_argument("--base-dir", default=".", help="Project root where SimFlow writes .simflow and reports")
    parser.add_argument("--project-root", help="Project root where SimFlow writes .simflow and reports")
    parser.add_argument("--calc-dir", default=".", help="Calculation directory relative to base-dir")
    parser.add_argument("--options", default="{}", help="JSON options")
    args = parser.parse_args()

    try:
        result = orchestrate_vasp_task(
            task=args.task,
            base_dir=args.project_root or args.base_dir,
            calc_dir=args.calc_dir,
            options=json.loads(args.options),
        )
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
