#!/usr/bin/env python3
"""Prepare one compact LAMMPS run plan without executing LAMMPS."""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
HPC_SERVER_DIR = REPO_ROOT / "mcp" / "servers" / "hpc"
INPUT_ROOT = Path(__file__).resolve().parent / "input"
sys.path.insert(0, str(REPO_ROOT))

from runtime.simflow_core.records import inspect_project, record_event


def _load_hpc_server():
    sys.path.insert(0, str(HPC_SERVER_DIR))
    spec = importlib.util.spec_from_file_location("simflow_lammps_example_hpc", HPC_SERVER_DIR / "server.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def run_lammps_safe_example(project_root: Path) -> dict:
    project_root = project_root.expanduser().resolve()
    work_dir = project_root / "calculation" / "lammps_safe"
    work_dir.mkdir(parents=True, exist_ok=True)
    for name in ("in.lammps", "data.lammps"):
        shutil.copyfile(INPUT_ROOT / name, work_dir / name)
    script = work_dir / "run_lammps.sh"
    script.write_text("#!/bin/bash\nset -euo pipefail\nlmp -in in.lammps\n", encoding="utf-8")
    script.chmod(0o755)

    server = _load_hpc_server()
    planned = server.handle_request({
        "tool": "plan",
        "params": {
            "project_root": str(project_root),
            "script_path": "calculation/lammps_safe/run_lammps.sh",
            "input_paths": [
                "calculation/lammps_safe/in.lammps",
                "calculation/lammps_safe/data.lammps",
            ],
            "scheduler": "local",
            "resources": {"nodes": 1, "ntasks": 1, "walltime": "00:01:00"},
        },
    })
    if planned.get("status") != "success":
        return {"status": "error", "project_root": str(project_root), "plan": planned}

    plan = planned["data"]
    blocked_submit = server.handle_request({
        "tool": "submit",
        "params": {"project_root": str(project_root), "run_plan_hash": plan["run_plan_hash"]},
    })
    record = record_event(
        str(project_root),
        kind="artifact",
        summary="LAMMPS safe dry-run package",
        status="planned",
        stage="computation",
        artifacts=[
            {"path": "calculation/lammps_safe/in.lammps", "role": "lammps_input"},
            {"path": "calculation/lammps_safe/data.lammps", "role": "lammps_data"},
            {"path": "calculation/lammps_safe/run_lammps.sh", "role": "job_script"},
            {"path": plan["plan_path"], "role": "immutable_run_plan"},
        ],
        next_action="request approval only if real LAMMPS execution is desired",
        details={
            "software": "lammps",
            "run_plan_hash": plan["run_plan_hash"],
            "credential_scan_status": plan["credential_scan"]["status"],
            "synthetic_fixture": True,
            "real_submit": False,
        },
    )
    inspected = inspect_project(str(project_root), include_legacy=False)
    summary = {
        "status": "success",
        "project_root": str(project_root),
        "software": "lammps",
        "real_submit": False,
        "run_plan_hash": plan["run_plan_hash"],
        "run_plan_status": plan["status"],
        "credential_scan_status": plan["credential_scan"]["status"],
        "submit_blocked": blocked_submit.get("status") == "error",
        "approval_required": blocked_submit.get("approval_required") is True,
        "record_id": record["record_id"],
        "record_count": inspected["record_count"],
        "checkpoint_count": inspected["project"]["counts"]["by_kind"].get("checkpoint", 0),
        "important_paths": {
            "input": "calculation/lammps_safe/in.lammps",
            "data": "calculation/lammps_safe/data.lammps",
            "script": "calculation/lammps_safe/run_lammps.sh",
            "run_plan": plan["plan_path"],
            "records": ".simflow/records.jsonl",
        },
    }
    report_path = project_root / ".simflow" / "reports" / "lammps_safe_example_summary.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    summary["important_paths"]["summary"] = ".simflow/reports/lammps_safe_example_summary.json"
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the compact LAMMPS safe dry-run example")
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()
    result = run_lammps_safe_example(Path(args.project_root))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if result.get("status") != "success":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
