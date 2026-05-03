#!/usr/bin/env python3
"""Manage workflow checkpoints.

Provides create, list, and restore operations for workflow checkpoints.
Wraps runtime/lib/checkpoint.py with a CLI interface.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from runtime.lib.checkpoint import create_checkpoint, list_checkpoints, restore_checkpoint
from runtime.lib.state import read_state


def manage_checkpoint(workflow_dir: str, action: str, checkpoint_id: str = None) -> dict:
    """Perform checkpoint management action."""
    wf_dir = Path(workflow_dir)

    if action == "create":
        state = read_state(str(wf_dir))
        if not state:
            return {"status": "error", "message": "No workflow state found"}
        result = create_checkpoint(
            str(wf_dir),
            workflow_id=state.get("workflow_id", "unknown"),
            stage=state.get("current_stage", "unknown"),
        )
        return {"status": "success", "action": "create", "checkpoint": result}

    elif action == "list":
        checkpoints = list_checkpoints(str(wf_dir))
        return {"status": "success", "action": "list", "checkpoints": checkpoints}

    elif action == "restore":
        if not checkpoint_id:
            return {"status": "error", "message": "checkpoint_id required for restore action"}
        result = restore_checkpoint(str(wf_dir), checkpoint_id)
        return {"status": "success", "action": "restore", "checkpoint_id": checkpoint_id, "result": result}

    elif action == "latest":
        checkpoints = list_checkpoints(str(wf_dir))
        if not checkpoints:
            return {"status": "error", "message": "No checkpoints found"}
        latest = checkpoints[-1]
        result = restore_checkpoint(str(wf_dir), latest["checkpoint_id"])
        return {"status": "success", "action": "restore_latest", "checkpoint": latest, "result": result}

    else:
        return {"status": "error", "message": "Unknown action: {}".format(action)}


def main():
    parser = argparse.ArgumentParser(description="Manage workflow checkpoints")
    parser.add_argument("--workflow-dir", required=True, help="Path to .simflow directory")
    parser.add_argument("--action", required=True, choices=["create", "list", "restore", "latest"],
                        help="Checkpoint action")
    parser.add_argument("--checkpoint-id", help="Checkpoint ID (for restore)")
    args = parser.parse_args()

    try:
        result = manage_checkpoint(args.workflow_dir, args.action, args.checkpoint_id)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
