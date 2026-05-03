#!/usr/bin/env python3
"""Generate a handoff summary for workflow context transfer."""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.state import read_state
from lib.artifact import list_artifacts
from lib.checkpoint import get_latest_checkpoint


def generate_handoff(base_dir: str = ".") -> dict:
    """Generate a handoff summary."""
    workflow = read_state(base_dir, "workflow.json")
    stages = read_state(base_dir, "stages.json")
    artifacts = list_artifacts(base_dir=base_dir)
    latest_ckpt = get_latest_checkpoint(base_dir)

    # Determine current stage and progress
    current_stage = workflow.get("current_stage", "unknown")
    completed = [s for s, v in stages.items() if v.get("status") == "completed"]
    failed = [s for s, v in stages.items() if v.get("status") == "failed"]
    in_progress = [s for s, v in stages.items() if v.get("status") == "in_progress"]

    # Build artifact summary by stage
    artifacts_by_stage = {}
    for art in artifacts:
        stage = art.get("stage", "unknown")
        if stage not in artifacts_by_stage:
            artifacts_by_stage[stage] = []
        artifacts_by_stage[stage].append({
            "artifact_id": art["artifact_id"],
            "name": art["name"],
            "type": art["type"],
            "version": art["version"],
        })

    # Determine risks
    risks = []
    if failed:
        risks.append(f"Failed stages: {', '.join(failed)}")
    if not latest_ckpt:
        risks.append("No checkpoints exist")

    # Next steps
    next_steps = []
    if in_progress:
        next_steps.append(f"Continue stage: {in_progress[0]}")
    elif failed:
        next_steps.append(f"Retry failed stage: {failed[0]}")
    elif completed:
        # Find next stage in workflow
        all_stages = list(stages.keys())
        last_completed_idx = -1
        for s in completed:
            if s in all_stages:
                idx = all_stages.index(s)
                last_completed_idx = max(last_completed_idx, idx)
        if last_completed_idx + 1 < len(all_stages):
            next_steps.append(f"Start stage: {all_stages[last_completed_idx + 1]}")
        else:
            next_steps.append("Workflow complete")

    handoff = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "workflow_id": workflow.get("workflow_id"),
        "workflow_type": workflow.get("workflow_type"),
        "status": workflow.get("status"),
        "current_stage": current_stage,
        "progress": {
            "completed": completed,
            "in_progress": in_progress,
            "failed": failed,
        },
        "artifacts": artifacts_by_stage,
        "latest_checkpoint": {
            "checkpoint_id": latest_ckpt["checkpoint_id"] if latest_ckpt else None,
            "stage": latest_ckpt["stage_id"] if latest_ckpt else None,
            "created_at": latest_ckpt["created_at"] if latest_ckpt else None,
        },
        "risks": risks,
        "next_steps": next_steps,
        "needs_approval": bool(failed),
    }

    return handoff


def main():
    parser = argparse.ArgumentParser(description="Generate handoff summary")
    parser.add_argument("--base-dir", default=".", help="Base directory")
    parser.add_argument("--output", help="Output file (default: stdout)")
    args = parser.parse_args()

    handoff = generate_handoff(args.base_dir)

    if args.output:
        p = Path(args.output)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(handoff, f, indent=2, ensure_ascii=False)
        print(json.dumps({"status": "success", "path": str(p)}))
    else:
        print(json.dumps(handoff, indent=2))


if __name__ == "__main__":
    main()
