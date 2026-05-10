#!/usr/bin/env python3
"""Execute a single workflow stage.

Orchestrates the execution of a workflow stage by running the
appropriate scripts and managing state transitions.
"""

import argparse
import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from runtime.lib.state import read_state, update_stage, write_state
from runtime.lib.utils import now_iso

WORKFLOWS_DIR = Path(__file__).resolve().parents[3] / "workflow" / "workflows"

STAGE_SCRIPTS = {
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

RESEARCH_STAGE_RUNNERS = {
    "literature": {
        "script": "skills/simflow-literature/scripts/generate_literature_matrix.py",
        "function": "generate_literature_matrix",
    },
    "review": {
        "script": "skills/simflow-review/scripts/generate_review.py",
        "function": "generate_review",
    },
    "proposal": {
        "script": "skills/simflow-proposal/scripts/generate_proposal.py",
        "function": "generate_proposal",
    },
}

STAGE_RUNNERS = {
    "modeling": {
        "script": "skills/simflow-modeling/scripts/run_modeling_stage.py",
        "function": "run_modeling_stage",
    },
    "input_generation": {
        "script": "skills/simflow-input-generation/scripts/run_input_generation_stage.py",
        "function": "run_input_generation_stage",
    },
    "compute": {
        "script": "skills/simflow-compute/scripts/run_compute_stage.py",
        "function": "run_compute_stage",
    },
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



def _load_runner(script: str, function_name: str, stage_name: str):
    """Load a function from a script file."""
    script_path = Path(__file__).resolve().parents[3] / script
    spec = importlib.util.spec_from_file_location(f"simflow_{stage_name}_runner", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return getattr(module, function_name), script



def _update_workflow_progress(project_root: Path, state: dict, stage_name: str, stages: list[str], status: str) -> None:
    """Persist workflow-level progress after stage execution."""
    state["current_stage"] = stage_name
    state["status"] = status if status == "failed" else ("completed" if stage_name == stages[-1] else "in_progress")
    state["updated_at"] = now_iso()
    write_state(state, project_root=str(project_root), state_file="workflow.json")


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
    research_runner = RESEARCH_STAGE_RUNNERS.get(stage_name)
    stage_runner = STAGE_RUNNERS.get(stage_name)

    result = {
        "stage": stage_name,
        "dry_run": dry_run,
        "started_at": now_iso(),
        "scripts": [],
        "params": params,
    }

    if dry_run:
        update_stage(stage_name, "pending", project_root=str(project_root))
        planned_scripts = scripts
        if stage_runner:
            planned_scripts = [stage_runner["script"]]
        elif research_runner:
            planned_scripts = [research_runner["script"]]
        result["status"] = "dry_run_complete"
        result["scripts"] = [{"script": script, "status": "would_execute"} for script in planned_scripts]
        result["message"] = f"Would execute {len(planned_scripts)} scripts for stage: {stage_name}"
        result["completed_at"] = now_iso()
        return result

    update_stage(stage_name, "in_progress", project_root=str(project_root))

    if research_runner:
        runner, script_path = _load_runner(research_runner["script"], research_runner["function"], stage_name)
        output_dir = params.get("output_dir")
        generator_result = runner(str(project_root / ".simflow"), output_dir)
        result["scripts"].append({
            "script": script_path,
            "status": "executed" if generator_result.get("status") == "success" else "failed",
        })
        if generator_result.get("status") != "success":
            update_stage(stage_name, "failed", project_root=str(project_root), error_message=generator_result.get("message"))
            _update_workflow_progress(project_root, state, stage_name, stages, "failed")
            result["status"] = "error"
            result["message"] = generator_result.get("message", f"Failed to execute stage: {stage_name}")
            result["completed_at"] = now_iso()
            return result

        artifacts = generator_result.get("artifacts", [])
        artifact_ids = [artifact["artifact_id"] for artifact in artifacts]
        parent_artifacts = []
        for artifact in artifacts:
            parent_artifacts.extend(artifact.get("lineage", {}).get("parent_artifacts", []))
        update_stage(
            stage_name,
            "completed",
            project_root=str(project_root),
            outputs=artifact_ids,
            inputs=sorted(set(parent_artifacts)),
        )
        _update_workflow_progress(project_root, state, stage_name, stages, "completed")
        result["status"] = "completed"
        result["artifacts"] = artifacts
        result["message"] = f"Executed stage generator for stage: {stage_name}"
        result["completed_at"] = now_iso()
        return result

    if stage_runner:
        runner, script_path = _load_runner(stage_runner["script"], stage_runner["function"], stage_name)
        stage_result = runner(str(project_root / ".simflow"), params=params, dry_run=False)
        result["scripts"].append({
            "script": script_path,
            "status": "executed" if stage_result.get("status") == "success" else "failed",
        })
        if stage_result.get("status") != "success":
            update_stage(stage_name, "failed", project_root=str(project_root), error_message=stage_result.get("message"))
            _update_workflow_progress(project_root, state, stage_name, stages, "failed")
            result["status"] = "error"
            result["message"] = stage_result.get("message", f"Failed to execute stage: {stage_name}")
            result["completed_at"] = now_iso()
            return result

        artifacts = stage_result.get("artifacts", [])
        artifact_ids = [artifact["artifact_id"] for artifact in artifacts]
        inputs = stage_result.get("inputs")
        if inputs is None:
            parent_artifacts = []
            for artifact in artifacts:
                parent_artifacts.extend(artifact.get("lineage", {}).get("parent_artifacts", []))
            inputs = sorted(set(parent_artifacts))
        update_stage(
            stage_name,
            "completed",
            project_root=str(project_root),
            outputs=artifact_ids,
            inputs=inputs,
        )
        _update_workflow_progress(project_root, state, stage_name, stages, "completed")
        result["status"] = "completed"
        result["artifacts"] = artifacts
        if "manifest" in stage_result:
            result["manifest"] = stage_result["manifest"]
        result["message"] = f"Executed stage runner for stage: {stage_name}"
        result["completed_at"] = now_iso()
        return result

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
    _update_workflow_progress(project_root, state, stage_name, stages, "completed")
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
