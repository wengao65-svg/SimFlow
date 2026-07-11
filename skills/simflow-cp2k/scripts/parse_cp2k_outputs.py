#!/usr/bin/env python3
"""Parse CP2K outputs inside a SimFlow project."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from _common import resolve_cp2k_paths, write_json_verified
from runtime.simflow_core.result_contract import attach_simflow_result
from runtime.simflow_core.script_contracts import add_helper_recording_args, maybe_record_helper_run
from runtime.simflow_helpers.engines.parsers.cp2k_parser import CP2KParser


def parse_cp2k_outputs(project_root: str, calc_dir: str = ".", project: str | None = None) -> dict:
    """Parse CP2K outputs from a calculation directory and write analysis reports."""
    stage = "analysis_visualization"
    activity = "analysis"
    root, work_dir = resolve_cp2k_paths(project_root, calc_dir)
    parser = CP2KParser()
    analysis = parser.parse_outputs(str(work_dir), project=project)
    handoff = {
        "task": "parse",
        "analysis_status": analysis["status"],
        "next_steps": [
            "Review the parsed summary for final energy, convergence, and restart metadata.",
            "Use orchestrate_cp2k_task.py for a combined validation/analysis handoff.",
        ],
        "approval_needed": False,
    }
    files = {
        "analysis_report": write_json_verified(root, "reports/cp2k/analysis_report.json", analysis),
        "handoff_artifact": write_json_verified(root, "reports/cp2k/handoff_artifact.json", handoff),
    }
    result = {
        "status": "success",
        "analysis_report": analysis,
        "reports": files,
    }
    return attach_simflow_result(
        result,
        role="helper",
        activity=activity,
        legacy_status=result["status"],
        stage=stage,
        state_effect="none",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse CP2K outputs inside a SimFlow project")
    parser.add_argument("--project-root", required=True, help="User project root for .simflow and reports")
    parser.add_argument("--calc-dir", default=".", help="Calculation directory relative to project_root")
    parser.add_argument("--project", help="Optional CP2K project prefix to prefer when multiple outputs exist")
    add_helper_recording_args(parser, default_stage="analysis_visualization")
    args = parser.parse_args()

    try:
        result = parse_cp2k_outputs(
            project_root=args.project_root,
            calc_dir=args.calc_dir,
            project=args.project,
        )
        result = maybe_record_helper_run(
            args=args,
            result=result,
            script_path=Path(__file__).resolve(),
            helper_name="cp2k_parse_outputs",
            software="cp2k",
            output_paths=list(result.get("reports", {}).values()),
        )
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, indent=2, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
