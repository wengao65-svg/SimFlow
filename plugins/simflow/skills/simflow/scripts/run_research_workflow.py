#!/usr/bin/env python3
"""Run the canonical SimFlow research workflow from user intent."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from runtime.simflow_core.gates import check_gate
from runtime.simflow_core.script_contracts import add_helper_recording_args, maybe_record_helper_run
from runtime.simflow_core.state import read_state
from runtime.simflow_core.status import build_handoff_summary, build_project_status
from runtime.simflow_helpers.project.intake import CANONICAL_STAGE_SEQUENCE, init_research, normalize_entry_stage
from runtime.simflow_helpers.stages.pipeline import run_pipeline


CANONICAL_STAGES = CANONICAL_STAGE_SEQUENCE


def _read_input_text(input_file: str | None, text: str | None) -> str:
    if input_file:
        return Path(input_file).expanduser().read_text(encoding="utf-8")
    if text:
        return text
    raise ValueError("Provide --text or --input.")


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _important_paths(project_root: Path) -> dict[str, str]:
    return {
        "workflow_state": ".simflow/state/workflow.json",
        "artifact_registry": ".simflow/state/artifacts.json",
        "checkpoint_registry": ".simflow/state/checkpoints.json",
        "computation_dry_run": ".simflow/artifacts/compute/dry_run_report.json",
        "credential_scan": ".simflow/artifacts/security/credential_scan.json",
        "writing_results": ".simflow/reports/writing/results.md",
        "handoff_markdown": ".simflow/reports/handoff/final_handoff.md",
        "workflow_summary": ".simflow/reports/research_workflow_summary.json",
    }


def build_research_workflow_summary(project_root: Path, pipeline_result: dict[str, Any]) -> dict[str, Any]:
    """Build a compact user-facing summary for the research workflow run."""
    workflow = read_state(project_root=str(project_root), state_file="workflow.json")
    project_status = build_project_status(str(project_root))
    handoff = build_handoff_summary(str(project_root))
    dry_run_report = _read_json_if_exists(project_root / ".simflow" / "artifacts" / "compute" / "dry_run_report.json")
    hpc_gate = check_gate("hpc_submit", {"project_root": str(project_root)})

    return {
        "status": "success" if pipeline_result.get("status") == "success" else "error",
        "project_root": str(project_root),
        "workflow_id": workflow.get("workflow_id"),
        "workflow_status": workflow.get("status"),
        "current_stage": workflow.get("current_stage"),
        "target_stage": pipeline_result.get("target_stage"),
        "dry_run": pipeline_result.get("dry_run"),
        "stages_executed": pipeline_result.get("stages_executed", 0),
        "completed_stages": project_status.get("progress", {}).get("completed_stages", []),
        "artifact_summary": project_status.get("artifacts", {}),
        "checkpoint_summary": project_status.get("checkpoints", {}),
        "lineage_summary": project_status.get("lineage", {}),
        "risk_summary": project_status.get("risks", []),
        "next_actions": project_status.get("next_actions", []),
        "computation": {
            "dry_run_status": dry_run_report.get("status"),
            "script_hash": dry_run_report.get("script_hash"),
            "input_artifact_hash": dry_run_report.get("input_artifact_hash"),
            "hpc_submit_gate_status": hpc_gate.get("status"),
            "hpc_submit_gate_code": hpc_gate.get("code"),
        },
        "handoff": {
            "current_stage": handoff.get("current_stage"),
            "latest_checkpoint": handoff.get("latest_checkpoint"),
            "risks": handoff.get("risks", []),
            "next_actions": handoff.get("next_actions", []),
        },
        "important_paths": _important_paths(project_root),
        "pipeline": {
            "status": pipeline_result.get("status"),
            "message": pipeline_result.get("message"),
            "checkpoint_id": pipeline_result.get("checkpoint_id"),
        },
    }


def run_research_workflow(
    *,
    project_root: str,
    input_text: str,
    target_stage: str = "writing",
    entry_stage: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Initialize and run the canonical research workflow."""
    root = Path(project_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    normalized_entry = normalize_entry_stage(entry_stage) if entry_stage else None
    normalized_target = normalize_entry_stage(target_stage)
    if normalized_entry and CANONICAL_STAGES.index(normalized_target) < CANONICAL_STAGES.index(normalized_entry):
        raise ValueError(f"target_stage {target_stage} is earlier than entry_stage {entry_stage}")

    init_result = init_research(input_text=input_text, output_dir=str(root), entry_stage=normalized_entry)
    pipeline_result = run_pipeline(str(root / ".simflow"), target_stage=target_stage, dry_run=dry_run)
    summary = build_research_workflow_summary(root, pipeline_result)
    summary["init"] = {
        "status": init_result.get("status"),
        "workflow_type": init_result.get("workflow_type"),
        "current_stage": init_result.get("current_stage"),
        "entry_stage": init_result.get("metadata", {}).get("entry_point"),
    }

    summary_path = root / ".simflow" / "reports" / "research_workflow_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a SimFlow literature-to-writing research workflow")
    parser.add_argument("--input", dest="input_file", help="Input file containing structured research intent")
    parser.add_argument("--text", help="Inline structured research intent")
    parser.add_argument("--project-root", required=True, help="User project root where .simflow will be written")
    parser.add_argument("--entry-stage", choices=CANONICAL_STAGES, help="Canonical stage to enter from")
    parser.add_argument("--target-stage", default="writing", choices=CANONICAL_STAGES, help="Canonical stage to run through")
    parser.add_argument("--dry-run", action="store_true", help="Plan stages without executing helper scripts")
    add_helper_recording_args(parser, default_stage="writing")
    args = parser.parse_args()

    try:
        result = run_research_workflow(
            project_root=args.project_root,
            input_text=_read_input_text(args.input_file, args.text),
            target_stage=args.target_stage,
            entry_stage=args.entry_stage,
            dry_run=args.dry_run,
        )
        summary_path = Path(args.project_root).expanduser().resolve() / ".simflow" / "reports" / "research_workflow_summary.json"
        result = maybe_record_helper_run(
            args=args,
            result=result,
            script_path=Path(__file__).resolve(),
            helper_name="run_research_workflow",
            input_paths=[args.input_file] if args.input_file else [],
            output_paths=[str(summary_path)],
            metadata={"entry_stage": args.entry_stage, "target_stage": args.target_stage, "dry_run": args.dry_run},
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        if result.get("status") != "success":
            raise SystemExit(1)
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, indent=2, ensure_ascii=False))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
