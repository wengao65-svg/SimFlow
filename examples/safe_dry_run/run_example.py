#!/usr/bin/env python3
"""Run a redistributable SimFlow dry-run example.

The example writes all generated state under the user-provided project root.
It never submits a local, remote, or HPC job.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from runtime.simflow_core.artifacts import list_artifacts
from runtime.simflow_core.gates import check_gate
from runtime.simflow_core.readiness import build_stage_readiness
from runtime.simflow_core.state import read_state
from runtime.simflow_core.status import build_handoff_summary, build_project_status
from runtime.simflow_helpers.project.intake import init_research
from runtime.simflow_helpers.stages.pipeline import run_pipeline


SAFE_INPUT = "\n".join([
    "goal: prepare a traceable Si dry-run evidence package",
    "material: Si diamond",
    "software: vasp",
    "method: dft",
    'parameters: {"encut": 520, "kppa": 100, "structure_type": "diamond", "lattice_param": 5.43, "elements": ["Si"]}',
    "note: This safe example uses synthetic literature metadata and dry-run computation evidence only.",
])


def run_safe_example(project_root: Path, target_stage: str = "writing") -> dict:
    project_root = project_root.expanduser().resolve()
    project_root.mkdir(parents=True, exist_ok=True)

    init_result = init_research(input_text=SAFE_INPUT, output_dir=str(project_root))
    pipeline_result = run_pipeline(str(project_root / ".simflow"), target_stage=target_stage, dry_run=False)
    if pipeline_result.get("status") != "success":
        return {
            "status": "error",
            "project_root": str(project_root),
            "init": init_result,
            "pipeline": pipeline_result,
        }

    workflow = read_state(project_root=str(project_root), state_file="workflow.json")
    status = build_project_status(str(project_root))
    handoff = build_handoff_summary(str(project_root))
    computation_readiness = build_stage_readiness(str(project_root), stage="computation")
    hpc_submit_gate = check_gate("hpc_submit", {"project_root": str(project_root)})
    dry_run_report_path = project_root / ".simflow" / "artifacts" / "compute" / "dry_run_report.json"
    dry_run_status = None
    if dry_run_report_path.exists():
        dry_run_status = json.loads(dry_run_report_path.read_text(encoding="utf-8")).get("status")
    artifacts = list_artifacts(project_root=str(project_root))
    checkpoints = read_state(project_root=str(project_root), state_file="checkpoints.json")

    summary = {
        "status": "success",
        "project_root": str(project_root),
        "workflow_id": workflow.get("workflow_id"),
        "current_stage": workflow.get("current_stage"),
        "workflow_status": workflow.get("status"),
        "target_stage": target_stage,
        "artifact_count": len(artifacts),
        "checkpoint_count": len(checkpoints),
        "computation_readiness": computation_readiness.get("readiness_status"),
        "dry_run_status": dry_run_status,
        "hpc_submit_gate_status": hpc_submit_gate.get("status"),
        "latest_checkpoint": status.get("checkpoints", {}).get("latest"),
        "next_actions": status.get("next_actions", []),
        "handoff": handoff,
        "important_paths": {
            "state": ".simflow/state/workflow.json",
            "artifacts": ".simflow/state/artifacts.json",
            "dry_run_report": ".simflow/artifacts/compute/dry_run_report.json",
            "credential_scan": ".simflow/artifacts/security/credential_scan.json",
            "handoff": ".simflow/reports/handoff/final_handoff.md",
        },
    }

    report_path = project_root / ".simflow" / "reports" / "safe_example_summary.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    summary["important_paths"]["safe_example_summary"] = ".simflow/reports/safe_example_summary.json"
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the SimFlow safe dry-run example")
    parser.add_argument("--project-root", required=True, help="Disposable project directory for generated .simflow state")
    parser.add_argument("--target-stage", default="writing", help="Canonical target stage to run through")
    args = parser.parse_args()

    result = run_safe_example(Path(args.project_root), target_stage=args.target_stage)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if result.get("status") != "success":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
