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

from _common import ensure_cp2k_project, finalize_stage, register_report, write_json_verified
from runtime.lib.parsers.cp2k_parser import CP2KParser


def parse_cp2k_outputs(project_root: str, calc_dir: str = ".", project: str | None = None) -> dict:
    """Parse CP2K outputs from a calculation directory and write analysis reports."""
    root, state = ensure_cp2k_project(project_root, "analysis")
    work_dir = (root / calc_dir).resolve()
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
    artifacts = [
        register_report(root, "analysis", "parse", "analysis_report", files["analysis_report"]),
        register_report(root, "analysis", "parse", "handoff_artifact", files["handoff_artifact"], artifact_type="handoff"),
    ]
    checkpoint = finalize_stage(
        root,
        state,
        "analysis",
        "parse",
        files,
        "success" if analysis["status"] == "parsed" else "failed",
        "Parsed CP2K outputs and wrote analysis report.",
    )
    return {
        "status": "success",
        "analysis_report": analysis,
        "reports": files,
        "artifacts": artifacts,
        "checkpoint": checkpoint,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse CP2K outputs inside a SimFlow project")
    parser.add_argument("--project-root", required=True, help="User project root for .simflow and reports")
    parser.add_argument("--calc-dir", default=".", help="Calculation directory relative to project_root")
    parser.add_argument("--project", help="Optional CP2K project prefix to prefer when multiple outputs exist")
    args = parser.parse_args()

    try:
        result = parse_cp2k_outputs(
            project_root=args.project_root,
            calc_dir=args.calc_dir,
            project=args.project,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, indent=2, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
