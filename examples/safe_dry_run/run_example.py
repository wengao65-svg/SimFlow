#!/usr/bin/env python3
"""Exercise the compact SimFlow dry-run path without executing a job."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
HPC_SERVER_DIR = REPO_ROOT / "mcp" / "servers" / "hpc"
sys.path.insert(0, str(REPO_ROOT))

from runtime.simflow_core.records import inspect_project, record_event


def _load_hpc_server():
    sys.path.insert(0, str(HPC_SERVER_DIR))
    spec = importlib.util.spec_from_file_location("simflow_safe_example_hpc", HPC_SERVER_DIR / "server.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def run_safe_example(project_root: Path) -> dict:
    project_root = project_root.expanduser().resolve()
    calc_dir = project_root / "calculation"
    calc_dir.mkdir(parents=True, exist_ok=True)
    script = calc_dir / "job.sh"
    input_file = calc_dir / "input.json"
    script.write_text("#!/bin/bash\nset -euo pipefail\necho should-not-run\n", encoding="utf-8")
    script.chmod(0o755)
    input_file.write_text(
        json.dumps({"material": "Si", "mode": "redistributable_dry_run"}, indent=2) + "\n",
        encoding="utf-8",
    )

    server = _load_hpc_server()
    planned = server.handle_request({
        "tool": "plan",
        "params": {
            "project_root": str(project_root),
            "script_path": "calculation/job.sh",
            "input_paths": ["calculation/input.json"],
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
        kind="milestone",
        summary="Redistributable dry-run plan prepared",
        status="planned",
        artifacts=[
            {"path": "calculation/job.sh", "role": "job_script"},
            {"path": "calculation/input.json", "role": "input"},
            {"path": plan["plan_path"], "role": "immutable_run_plan"},
        ],
        next_action="request approval only if real execution is desired",
        details={
            "run_plan_hash": plan["run_plan_hash"],
            "scheduler": plan["scheduler"],
            "credential_scan_status": plan["credential_scan"]["status"],
            "real_submit": False,
        },
    )
    inspected = inspect_project(str(project_root), include_legacy=False)
    summary = {
        "status": "success",
        "project_root": str(project_root),
        "run_plan_hash": plan["run_plan_hash"],
        "run_plan_status": plan["status"],
        "credential_scan_status": plan["credential_scan"]["status"],
        "submit_blocked": blocked_submit.get("status") == "error",
        "approval_required": blocked_submit.get("approval_required") is True,
        "record_id": record["record_id"],
        "record_count": inspected["record_count"],
        "checkpoint_count": inspected["project"]["counts"]["by_kind"].get("checkpoint", 0),
        "important_paths": {
            "project": ".simflow/project.json",
            "records": ".simflow/records.jsonl",
            "run_plan": plan["plan_path"],
            "script": "calculation/job.sh",
            "input": "calculation/input.json",
        },
    }
    report_path = project_root / ".simflow" / "reports" / "safe_example_summary.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    summary["important_paths"]["summary"] = ".simflow/reports/safe_example_summary.json"
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the compact SimFlow safe dry-run example")
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()
    result = run_safe_example(Path(args.project_root))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if result.get("status") != "success":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
