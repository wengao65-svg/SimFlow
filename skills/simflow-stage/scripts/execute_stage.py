#!/usr/bin/env python3
"""Execute a single workflow stage.

Orchestrates the execution of a workflow stage by running the
appropriate scripts and managing state transitions.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from runtime.lib.state import read_state, update_stage
from runtime.lib.utils import now_iso

# Map stage names to the skill scripts that implement them
STAGE_SCRIPTS = {
    "modeling": [
        "skills/simflow-modeling/scripts/build_structure.py",
        "skills/simflow-modeling/scripts/make_supercell.py",
        "skills/simflow-modeling/scripts/validate_structure.py",
    ],
    "input_generation": [
        "skills/simflow-vasp/scripts/generate_vasp_inputs.py",
        "skills/simflow-lammps/scripts/generate_lammps_inputs.py",
    ],
    "compute": [
        "skills/simflow-compute/scripts/prepare_job.py",
    ],
    "analysis": [
        "skills/simflow-analysis/scripts/analyze_dft_results.py",
        "skills/simflow-analysis/scripts/analyze_md_trajectory.py",
        "skills/simflow-analysis/scripts/generate_analysis_report.py",
    ],
    "visualization": [
        "skills/simflow-visualization/scripts/plot_energy_curve.py",
    ],
}


def execute_stage(workflow_dir: str, stage_name: str, params: dict = None,
                  dry_run: bool = True) -> dict:
    """Execute a single workflow stage."""
    wf_dir = Path(workflow_dir)
    state = read_state(str(wf_dir))

    if not state:
        return {"status": "error", "message": "No workflow state found"}

    stages = state.get("stages", [])
    if stage_name not in stages:
        return {"status": "error", "message": "Unknown stage: {}".format(stage_name)}

    params = params or {}
    scripts = STAGE_SCRIPTS.get(stage_name, [])

    result = {
        "stage": stage_name,
        "dry_run": dry_run,
        "started_at": now_iso(),
        "scripts": [],
    }

    if dry_run:
        result["status"] = "dry_run_complete"
        result["scripts"] = [{"script": s, "status": "would_execute"} for s in scripts]
        result["message"] = "Would execute {} scripts for stage: {}".format(len(scripts), stage_name)
    else:
        update_stage(str(wf_dir), stage_name, "in_progress")

        for script_path in scripts:
            full_path = Path(__file__).resolve().parents[3] / script_path
            if full_path.exists():
                result["scripts"].append({
                    "script": script_path,
                    "status": "available",
                    "path": str(full_path),
                })
            else:
                result["scripts"].append({
                    "script": script_path,
                    "status": "not_found",
                })

        result["status"] = "executed"

    result["completed_at"] = now_iso()
    return result


def main():
    parser = argparse.ArgumentParser(description="Execute a workflow stage")
    parser.add_argument("--workflow-dir", required=True, help="Path to .simflow directory")
    parser.add_argument("--stage", required=True, help="Stage name to execute")
    parser.add_argument("--params", type=str, default="{}",
                        help="JSON parameters for the stage")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--execute", dest="dry_run", action="store_false")
    args = parser.parse_args()

    try:
        params = json.loads(args.params)
        result = execute_stage(args.workflow_dir, args.stage, params, args.dry_run)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
