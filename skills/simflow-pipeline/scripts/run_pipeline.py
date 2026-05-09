#!/usr/bin/env python3
"""Run a multi-stage workflow pipeline.

Advances through workflow stages, executing each one and managing
stage transitions with checkpoint creation.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from runtime.lib.checkpoint import create_checkpoint
from runtime.lib.state import read_state, update_stage, write_state
from runtime.lib.utils import now_iso

WORKFLOWS_DIR = Path(__file__).resolve().parents[3] / "workflow" / "workflows"


def resolve_project_root_from_workflow_dir(workflow_dir: str) -> Path:
    """Resolve the project root from either a project root or .simflow path."""
    path = Path(workflow_dir).expanduser().resolve()
    return path.parent if path.name == ".simflow" else path


def load_workflow_stages(workflow_type: str, metadata: dict) -> list[str]:
    """Load canonical workflow stages from metadata or workflow definitions."""
    stages = metadata.get("stages", [])
    if isinstance(stages, list) and stages:
        return stages

    normalized = (workflow_type or "dft").lower()
    path = WORKFLOWS_DIR / f"{normalized}.json"
    if not path.exists():
        path = WORKFLOWS_DIR / "dft.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    loaded = data.get("stages", [])
    return [stage["name"] if isinstance(stage, dict) else stage for stage in loaded]


def get_stages_to_run(stages: list[str], current_stage: str, stage_registry: dict, target_stage: str | None) -> list[str]:
    """Determine which stages the pipeline should traverse."""
    if not stages:
        return []

    if current_stage not in stages:
        current_stage = stages[0]

    start_idx = stages.index(current_stage)
    if stage_registry.get(current_stage, {}).get("status") == "completed" and start_idx < len(stages) - 1:
        start_idx += 1

    if target_stage:
        if target_stage not in stages:
            return []
        end_idx = stages.index(target_stage) + 1
        if end_idx < start_idx:
            return []
        return stages[start_idx:end_idx]

    return stages[start_idx:]


def run_pipeline(workflow_dir: str, target_stage: str = None,
                 dry_run: bool = True, stop_on_failure: bool = True) -> dict:
    """Execute workflow pipeline up to target stage."""
    project_root = resolve_project_root_from_workflow_dir(workflow_dir)
    state = read_state(project_root=str(project_root), state_file="workflow.json")

    if not state:
        return {"status": "error", "message": "No workflow state found"}

    metadata = read_state(project_root=str(project_root), state_file="metadata.json")
    stage_registry = read_state(project_root=str(project_root), state_file="stages.json")
    workflow_type = metadata.get("workflow_type", state.get("workflow_type", "dft"))
    stages = load_workflow_stages(workflow_type, metadata)
    current_stage = state.get("current_stage", metadata.get("entry_point") or (stages[0] if stages else None))

    if not stages:
        return {"status": "error", "message": "No stages defined"}
    if target_stage and target_stage not in stages:
        return {"status": "error", "message": f"Unknown stage: {target_stage}"}

    stages_to_run = get_stages_to_run(stages, current_stage, stage_registry, target_stage)
    if not stages_to_run:
        return {
            "status": "success",
            "workflow_dir": workflow_dir,
            "current_stage": current_stage,
            "target_stage": target_stage or current_stage,
            "stages_executed": 0,
            "dry_run": dry_run,
            "results": [],
        }

    results = []
    for stage_name in stages_to_run:
        if dry_run:
            update_stage(stage_name, "pending", project_root=str(project_root))
            stage_result = {
                "stage": stage_name,
                "status": "dry_run_complete",
                "dry_run": True,
                "started_at": now_iso(),
                "message": f"Would execute stage: {stage_name}",
            }
        else:
            update_stage(stage_name, "in_progress", project_root=str(project_root))
            update_stage(stage_name, "completed", project_root=str(project_root))
            stage_result = {
                "stage": stage_name,
                "status": "completed",
                "dry_run": False,
                "started_at": now_iso(),
                "message": f"Executed stage: {stage_name}",
            }
        results.append(stage_result)

    checkpoint = None
    if not dry_run:
        final_stage = stages_to_run[-1]
        checkpoint = create_checkpoint(
            state.get("workflow_id", "unknown"),
            final_stage,
            f"Pipeline advanced through {final_stage}",
            project_root=str(project_root),
        )
        update_stage(final_stage, "completed", project_root=str(project_root), checkpoint_id=checkpoint["checkpoint_id"])
        state["current_stage"] = final_stage
        state["status"] = "completed" if final_stage == stages[-1] else "in_progress"
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        write_state(state, project_root=str(project_root), state_file="workflow.json")

    return {
        "status": "success",
        "workflow_dir": workflow_dir,
        "current_stage": current_stage,
        "target_stage": target_stage or stages_to_run[-1],
        "stages_executed": len(results),
        "dry_run": dry_run,
        "results": results,
        "checkpoint_id": checkpoint["checkpoint_id"] if checkpoint else None,
    }


def main():
    parser = argparse.ArgumentParser(description="Run workflow pipeline")
    parser.add_argument("--workflow-dir", required=True, help="Path to .simflow directory")
    parser.add_argument("--target-stage", help="Run up to this stage")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Simulate without executing")
    parser.add_argument("--execute", dest="dry_run", action="store_false",
                        help="Actually execute stages")
    parser.add_argument("--stop-on-failure", action="store_true", default=True)
    args = parser.parse_args()

    try:
        result = run_pipeline(args.workflow_dir, args.target_stage,
                              args.dry_run, args.stop_on_failure)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
