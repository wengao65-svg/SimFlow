#!/usr/bin/env python3
"""Run a multi-stage workflow pipeline.

Advances through workflow stages, executing each one and managing
stage transitions with checkpoint creation.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from runtime.lib.state import read_state, update_stage
from runtime.lib.checkpoint import create_checkpoint
from runtime.lib.utils import generate_id, now_iso


def run_pipeline(workflow_dir: str, target_stage: str = None,
                 dry_run: bool = True, stop_on_failure: bool = True) -> dict:
    """Execute workflow pipeline up to target stage."""
    wf_dir = Path(workflow_dir)
    state = read_state(str(wf_dir))

    if not state:
        return {"status": "error", "message": "No workflow state found"}

    stages = state.get("stages", [])
    current_stage = state.get("current_stage", stages[0] if stages else None)

    if not stages:
        return {"status": "error", "message": "No stages defined"}

    # Determine which stages to execute
    if target_stage:
        if target_stage not in stages:
            return {"status": "error", "message": "Unknown stage: {}".format(target_stage)}
        start_idx = stages.index(current_stage) if current_stage in stages else 0
        end_idx = stages.index(target_stage) + 1
        stages_to_run = stages[start_idx:end_idx]
    else:
        start_idx = stages.index(current_stage) if current_stage in stages else 0
        stages_to_run = stages[start_idx:]

    results = []
    for stage_name in stages_to_run:
        stage_result = {
            "stage": stage_name,
            "status": "pending",
            "dry_run": dry_run,
            "started_at": now_iso(),
        }

        if dry_run:
            stage_result["status"] = "dry_run_complete"
            stage_result["message"] = "Would execute stage: {}".format(stage_name)
        else:
            # Update state to in_progress
            update_stage(str(wf_dir), stage_name, "in_progress")
            stage_result["status"] = "in_progress"

        results.append(stage_result)

    # Create checkpoint at end of pipeline run
    if not dry_run and results:
        checkpoint = create_checkpoint(
            str(wf_dir),
            workflow_id=state.get("workflow_id", "unknown"),
            stage=stages_to_run[-1] if stages_to_run else current_stage,
        )

    return {
        "status": "success",
        "workflow_dir": workflow_dir,
        "current_stage": current_stage,
        "target_stage": target_stage or stages[-1],
        "stages_executed": len(results),
        "dry_run": dry_run,
        "results": results,
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
