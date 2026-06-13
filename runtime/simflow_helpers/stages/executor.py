#!/usr/bin/env python3
"""Execute canonical workflow stages through bounded helper runners."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from runtime.simflow_core.state import read_state, update_stage, write_state
from runtime.simflow_core.utils import now_iso
from runtime.simflow_helpers.stages.progress import (
    load_workflow_activities,
    resolve_project_root_from_workflow_dir,
)


def _runner(script: str, function: str, activity: str, *, stage_runner: bool = False) -> dict[str, Any]:
    return {
        "script": script,
        "function": function,
        "activity": activity,
        "stage_runner": stage_runner,
    }


CANONICAL_STAGE_RUNNERS = {
    "literature_review": [
        _runner("skills/simflow-literature-review/scripts/generate_literature_matrix.py", "generate_literature_matrix", "literature"),
        _runner("skills/simflow-literature-review/scripts/generate_review.py", "generate_review", "review"),
    ],
    "proposal": [
        _runner("skills/simflow-proposal/scripts/generate_proposal.py", "generate_proposal", "proposal"),
    ],
    "modeling": [
        _runner("skills/simflow-modeling/scripts/run_modeling_stage.py", "run_modeling_stage", "modeling", stage_runner=True),
    ],
    "computation": [
        _runner("skills/simflow-computation/scripts/run_input_generation_stage.py", "run_input_generation_stage", "input_generation", stage_runner=True),
        _runner("skills/simflow-computation/scripts/run_compute_stage.py", "run_compute_stage", "compute", stage_runner=True),
    ],
    "analysis_visualization": [
        _runner("skills/simflow-analysis-visualization/scripts/run_analysis_stage.py", "run_analysis_stage", "analysis", stage_runner=True),
        _runner("skills/simflow-analysis-visualization/scripts/run_visualization_stage.py", "run_visualization_stage", "visualization", stage_runner=True),
    ],
    "writing": [
        _runner("skills/simflow-writing/scripts/run_writing_stage.py", "run_writing_stage", "writing", stage_runner=True),
    ],
}


def load_workflow_stages(workflow_type: str, metadata: dict[str, Any] | None = None) -> list[str]:
    """Load canonical stages from canonical recipes."""
    return load_workflow_activities(workflow_type, metadata)


def _load_runner(script: str, function_name: str, stage_name: str):
    """Load a function from a helper script file."""
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


def _artifact_ids(artifacts: list[dict[str, Any]]) -> list[str]:
    return [artifact["artifact_id"] for artifact in artifacts if artifact.get("artifact_id")]


def _inputs_from_artifacts(artifacts: list[dict[str, Any]]) -> list[str]:
    parent_artifacts: list[str] = []
    for artifact in artifacts:
        parent_artifacts.extend(artifact.get("lineage", {}).get("parent_artifacts", []))
    return sorted(set(parent_artifacts))


def _stage_inputs(stage_result: dict[str, Any], artifacts: list[dict[str, Any]]) -> list[str]:
    inputs = stage_result.get("inputs")
    if inputs is not None:
        return sorted(set(inputs))
    return _inputs_from_artifacts(artifacts)


def _execute_runner(
    runner_spec: dict[str, Any],
    project_root: Path,
    params: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    runner, script_path = _load_runner(runner_spec["script"], runner_spec["function"], runner_spec["activity"])
    if runner_spec.get("stage_runner"):
        return runner(str(project_root / ".simflow"), params=params, dry_run=False), script_path
    return runner(str(project_root / ".simflow")), script_path


def execute_stage(workflow_dir: str, stage_name: str, params: dict | None = None, dry_run: bool = True) -> dict:
    """Execute a canonical workflow stage."""
    project_root = resolve_project_root_from_workflow_dir(workflow_dir)
    state = read_state(project_root=str(project_root), state_file="workflow.json")

    if not state:
        return {"status": "error", "message": "No workflow state found"}

    metadata = read_state(project_root=str(project_root), state_file="metadata.json")
    workflow_type = metadata.get("workflow_type", state.get("workflow_type", "dft"))
    stages = load_workflow_stages(workflow_type, metadata)
    if stage_name not in stages:
        return {"status": "error", "message": f"Unknown stage: {stage_name}"}

    params = params or {}
    runner_specs = CANONICAL_STAGE_RUNNERS.get(stage_name, [])
    result: dict[str, Any] = {
        "stage": stage_name,
        "dry_run": dry_run,
        "started_at": now_iso(),
        "scripts": [],
        "params": params,
    }

    if dry_run:
        update_stage(stage_name, "pending", project_root=str(project_root))
        result["status"] = "dry_run_complete"
        result["scripts"] = [
            {"script": runner_spec["script"], "activity": runner_spec["activity"], "status": "would_execute"}
            for runner_spec in runner_specs
        ]
        result["message"] = f"Would execute {len(runner_specs)} helpers for stage: {stage_name}"
        result["completed_at"] = now_iso()
        return result

    update_stage(stage_name, "in_progress", project_root=str(project_root))
    aggregate_artifacts: list[dict[str, Any]] = []
    aggregate_inputs: set[str] = set()
    manifests: dict[str, Any] = {}

    for runner_spec in runner_specs:
        activity = runner_spec["activity"]
        stage_result, script_path = _execute_runner(runner_spec, project_root, params)
        success = stage_result.get("status") == "success"
        capability_warning = stage_result.get("status") == "capability_warning"
        result["scripts"].append({
            "script": script_path,
            "activity": activity,
            "status": "executed" if success else ("warning" if capability_warning else "failed"),
        })
        if capability_warning:
            update_stage(stage_name, "waiting", project_root=str(project_root), error_message=stage_result.get("message"))
            _update_workflow_progress(project_root, state, stage_name, stages, "in_progress")
            result["status"] = "capability_warning"
            result["message"] = stage_result.get("message")
            result["warning"] = stage_result
            result["completed_at"] = now_iso()
            return result
        if not success:
            message = stage_result.get("message", f"Failed to execute activity: {activity}")
            update_stage(stage_name, "failed", project_root=str(project_root), error_message=message)
            _update_workflow_progress(project_root, state, stage_name, stages, "failed")
            result["status"] = "error"
            result["message"] = message
            result["completed_at"] = now_iso()
            return result

        artifacts = stage_result.get("artifacts", [])
        inputs = _stage_inputs(stage_result, artifacts)
        aggregate_artifacts.extend(artifacts)
        aggregate_inputs.update(inputs)
        if "manifest" in stage_result:
            manifests[activity] = stage_result["manifest"]
            result["manifest"] = stage_result["manifest"]

    aggregate_outputs = _artifact_ids(aggregate_artifacts)
    if not aggregate_inputs:
        aggregate_inputs.update(_inputs_from_artifacts(aggregate_artifacts))
    update_stage(
        stage_name,
        "completed",
        project_root=str(project_root),
        outputs=aggregate_outputs,
        inputs=sorted(aggregate_inputs),
    )
    _update_workflow_progress(project_root, state, stage_name, stages, "completed")
    result["status"] = "completed"
    result["artifacts"] = aggregate_artifacts
    if manifests:
        result["manifests"] = manifests
    result["message"] = f"Executed {len(runner_specs)} helpers for stage: {stage_name}"
    result["completed_at"] = now_iso()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Execute a workflow stage")
    parser.add_argument("--workflow-dir", required=True, help="Path to .simflow directory")
    parser.add_argument("--stage", required=True, help="Stage name to execute")
    parser.add_argument("--params", type=str, default="{}", help="JSON parameters for the stage")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--execute", dest="dry_run", action="store_false")
    args = parser.parse_args()

    try:
        params = json.loads(args.params)
        result = execute_stage(args.workflow_dir, args.stage, params, args.dry_run)
        print(json.dumps(result, indent=2))
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
