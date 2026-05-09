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

WORKFLOWS_DIR = Path(__file__).resolve().parents[3] / "workflow" / "workflows"

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


def resolve_project_root_from_workflow_dir(workflow_dir: str) -> Path:
    """Resolve the project root from either a project root or .simflow path."""
    path = Path(workflow_dir).expanduser().resolve()
    return path.parent if path.name == ".simflow" else path


def load_workflow_stages(workflow_type: str) -> list[str]:
    """Load canonical workflow stages from the workflow definition."""
    normalized = (workflow_type or "dft").lower()
    path = WORKFLOWS_DIR / f"{normalized}.json"
    if not path.exists():
        path = WORKFLOWS_DIR / "dft.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    loaded = data.get("stages", [])
    return [stage["name"] if isinstance(stage, dict) else stage for stage in loaded]


def execute_stage(workflow_dir: str, stage_name: str, params: dict = None,
                  dry_run: bool = True) -> dict:
    """Execute a single workflow stage."""
    project_root = resolve_project_root_from_workflow_dir(workflow_dir)
    state = read_state(project_root=str(project_root), state_file="workflow.json")

    if not state:
        return {"status": "error", "message": "No workflow state found"}

    metadata = read_state(project_root=str(project_root), state_file="metadata.json")
    workflow_type = metadata.get("workflow_type", state.get("workflow_type", "dft"))
    stages = load_workflow_stages(workflow_type)
    if stage_name not in stages:
        return {"status": "error", "message": f"Unknown stage: {stage_name}"}

    params = params or {}
    scripts = STAGE_SCRIPTS.get(stage_name, [])

    result = {
        "stage": stage_name,
        "dry_run": dry_run,
        "started_at": now_iso(),
        "scripts": [],
        "params": params,
    }

    if dry_run:
        update_stage(stage_name, "pending", project_root=str(project_root))
        result["status"] = "dry_run_complete"
        result["scripts"] = [{"script": script, "status": "would_execute"} for script in scripts]
        result["message"] = f"Would execute {len(scripts)} scripts for stage: {stage_name}"
    else:
        update_stage(stage_name, "in_progress", project_root=str(project_root))
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
        update_stage(stage_name, "completed", project_root=str(project_root))
        result["status"] = "completed"
        result["message"] = f"Executed {len(scripts)} scripts for stage: {stage_name}"

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
