#!/usr/bin/env python3
"""Verify Milestone D final delivery artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from runtime.lib.artifact import register_artifact
from runtime.lib.state import read_state
from runtime.lib.verification import (
    VERIFY_REPORT_JSON,
    VERIFY_REPORT_MARKDOWN,
    build_final_delivery_report,
    persist_verification_state,
    write_verification_outputs,
)


def resolve_project_root_from_workflow_dir(workflow_dir: str) -> Path:
    path = Path(workflow_dir).expanduser().resolve()
    return path.parent if path.name == ".simflow" else path


def verify_workflow(workflow_dir: str, params: dict | None = None, dry_run: bool = False) -> dict[str, Any]:
    project_root = resolve_project_root_from_workflow_dir(workflow_dir)
    params = params or {}
    write_markdown_report = bool(
        params.get("write_markdown_report")
        or params.get("write_markdown")
        or params.get("write_report_markdown")
    )
    planned_outputs = [VERIFY_REPORT_JSON]
    if write_markdown_report:
        planned_outputs.append(VERIFY_REPORT_MARKDOWN)
    if dry_run:
        return {
            "status": "dry_run_complete",
            "verification_status": "pending",
            "planned_outputs": planned_outputs,
        }

    workflow = read_state(project_root=str(project_root), state_file="workflow.json")
    if not workflow:
        return {"status": "error", "message": "No workflow state found"}

    try:
        report = build_final_delivery_report(
            project_root=str(project_root),
            source_artifact_ids=params.get("source_artifact_ids"),
        )
        persist_verification_state(report, project_root=str(project_root))
        report = write_verification_outputs(
            report,
            project_root=str(project_root),
            write_markdown=write_markdown_report,
        )
    except Exception as exc:
        return {"status": "error", "message": str(exc)}

    parent_artifact_ids = list(
        dict.fromkeys(
            [
                *(params.get("parent_artifact_ids") or []),
                *report.get("source_artifact_ids", []),
            ]
        )
    )
    json_artifact = register_artifact(
        "verification_report.json",
        "verification_report",
        "writing",
        project_root=str(project_root),
        path=VERIFY_REPORT_JSON,
        parent_artifacts=parent_artifact_ids,
        parameters={
            "verification_status": report.get("status"),
            "check_names": [check.get("name") for check in report.get("checks", [])],
        },
        software=params.get("software"),
    )
    artifacts = [json_artifact]
    if write_markdown_report:
        markdown_artifact = register_artifact(
            "verification_report.md",
            "verification_report_markdown",
            "writing",
            project_root=str(project_root),
            path=VERIFY_REPORT_MARKDOWN,
            parent_artifacts=[json_artifact["artifact_id"], *parent_artifact_ids],
            parameters={"verification_status": report.get("status")},
            software=params.get("software"),
        )
        artifacts.append(markdown_artifact)

    return {
        "status": "success",
        "verification_status": report.get("status"),
        "artifacts": artifacts,
        "report": report,
        "outputs": planned_outputs,
        "warnings": report.get("warnings", []),
        "failures": report.get("failures", []),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify workflow final delivery artifacts")
    parser.add_argument("--workflow-dir", required=True, help="Path to .simflow directory")
    parser.add_argument("--params", type=str, default="{}", help="JSON parameters for verification")
    parser.add_argument("--dry-run", action="store_true", default=False)
    args = parser.parse_args()

    try:
        params = json.loads(args.params)
        result = verify_workflow(args.workflow_dir, params=params, dry_run=args.dry_run)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
