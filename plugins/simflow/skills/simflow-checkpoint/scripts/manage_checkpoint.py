#!/usr/bin/env python3
"""Manage workflow checkpoints.

Provides create, list, and restore operations for workflow checkpoints through
the canonical runtime.simflow_core checkpoint API.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from runtime.simflow_core.checkpoints import create_checkpoint, get_latest_checkpoint, list_checkpoints, restore_checkpoint
from runtime.simflow_core.result_contract import attach_simflow_result
from runtime.simflow_core.state import read_state, resolve_project_root


def _resolve_checkpoint_project_root(workflow_dir: str) -> Path:
    """Accept either a project root or its `.simflow` state directory."""
    path = Path(workflow_dir).expanduser()
    candidate = path.parent if path.name == ".simflow" else path
    return resolve_project_root(project_root=str(candidate))


def _state_admin_result(
    payload: dict,
    *,
    activity: str,
    state_effect: str,
    stage: str | None = None,
) -> dict:
    return attach_simflow_result(
        payload,
        role="state_admin",
        activity=activity,
        legacy_status=payload.get("status"),
        stage=stage,
        state_effect=state_effect,
    )


def manage_checkpoint(workflow_dir: str, action: str, checkpoint_id: str = None) -> dict:
    """Perform checkpoint management action."""
    project_root = _resolve_checkpoint_project_root(workflow_dir)

    if action == "create":
        state = read_state(project_root=str(project_root), state_file="workflow.json")
        if not state:
            return _state_admin_result(
                {
                    "status": "error",
                    "action": "create",
                    "project_root": str(project_root),
                    "message": "No workflow state found",
                },
                activity="checkpoint_create",
                state_effect="checkpoint_admin",
            )
        stage_id = state.get("current_stage") or state.get("entry_point") or "unknown"
        result = create_checkpoint(
            workflow_id=state.get("workflow_id", "unknown"),
            stage_id=stage_id,
            description=f"Checkpoint created by manage_checkpoint for {stage_id}",
            project_root=str(project_root),
        )
        return _state_admin_result(
            {
                "status": "success",
                "action": "create",
                "project_root": str(project_root),
                "checkpoint": result,
            },
            activity="checkpoint_create",
            state_effect="checkpoint_admin",
            stage=stage_id,
        )

    elif action == "list":
        checkpoints = list_checkpoints(project_root=str(project_root))
        return _state_admin_result(
            {
                "status": "success",
                "action": "list",
                "project_root": str(project_root),
                "checkpoint_count": len(checkpoints),
                "checkpoints": checkpoints,
            },
            activity="checkpoint_list",
            state_effect="none",
        )

    elif action == "restore":
        if not checkpoint_id:
            return _state_admin_result(
                {
                    "status": "error",
                    "action": "restore",
                    "project_root": str(project_root),
                    "message": "checkpoint_id required for restore action",
                },
                activity="checkpoint_restore",
                state_effect="checkpoint_admin",
            )
        result = restore_checkpoint(checkpoint_id, project_root=str(project_root))
        return _state_admin_result(
            {
                "status": "success",
                "action": "restore",
                "project_root": str(project_root),
                "checkpoint_id": checkpoint_id,
                "result": result,
            },
            activity="checkpoint_restore",
            state_effect="checkpoint_admin",
            stage=result.get("stage_id"),
        )

    elif action == "latest":
        latest = get_latest_checkpoint(project_root=str(project_root))
        if not latest:
            return _state_admin_result(
                {
                    "status": "error",
                    "action": "latest",
                    "project_root": str(project_root),
                    "message": "No checkpoints found",
                },
                activity="checkpoint_latest",
                state_effect="checkpoint_admin",
            )
        result = restore_checkpoint(latest["checkpoint_id"], project_root=str(project_root))
        return _state_admin_result(
            {
                "status": "success",
                "action": "latest",
                "project_root": str(project_root),
                "checkpoint": latest,
                "result": result,
            },
            activity="checkpoint_latest",
            state_effect="checkpoint_admin",
            stage=latest.get("stage_id"),
        )

    else:
        return _state_admin_result(
            {
                "status": "error",
                "action": action,
                "project_root": str(project_root),
                "message": "Unknown action: {}".format(action),
            },
            activity="checkpoint_unknown",
            state_effect="none",
        )


def main():
    parser = argparse.ArgumentParser(description="Manage workflow checkpoints")
    parser.add_argument("--workflow-dir", help="Path to a project root or its .simflow directory")
    parser.add_argument("--project-root", help="Explicit project root; overrides --workflow-dir when set")
    parser.add_argument("--action", required=True, choices=["create", "list", "restore", "latest"],
                        help="Checkpoint action")
    parser.add_argument("--checkpoint-id", help="Checkpoint ID (for restore)")
    args = parser.parse_args()
    workflow_dir = args.project_root or args.workflow_dir
    if not workflow_dir:
        parser.error("one of --workflow-dir or --project-root is required")

    resolved_project_root = None
    try:
        resolved_project_root = str(_resolve_checkpoint_project_root(workflow_dir))
        result = manage_checkpoint(workflow_dir, args.action, args.checkpoint_id)
        print(json.dumps(result, indent=2))
    except Exception as e:
        state_effect = "none" if args.action == "list" else "checkpoint_admin"
        payload = {
            "status": "error",
            "action": args.action,
            "message": str(e),
        }
        if resolved_project_root is not None:
            payload["project_root"] = resolved_project_root
        result = _state_admin_result(
            payload,
            activity=f"checkpoint_{args.action}",
            state_effect=state_effect,
        )
        print(json.dumps(result, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
