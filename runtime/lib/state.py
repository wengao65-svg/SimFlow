"""Workflow state management."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


SIMFLOW_DIR = ".simflow"
STATE_DIR = os.path.join(SIMFLOW_DIR, "state")


def get_simflow_path(base_dir: str = ".") -> Path:
    """Get the .simflow directory path."""
    return Path(base_dir) / SIMFLOW_DIR


def ensure_simflow_dir(base_dir: str = ".") -> Path:
    """Ensure .simflow directory structure exists."""
    sf = get_simflow_path(base_dir)
    dirs = [
        sf / "state",
        sf / "plans",
        sf / "artifacts",
        sf / "checkpoints",
        sf / "reports",
        sf / "logs",
        sf / "extensions" / "skills",
        sf / "memory",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    return sf


def read_state(base_dir: str = ".", state_file: str = "workflow.json") -> dict:
    """Read a state file from .simflow/state/."""
    path = Path(base_dir) / STATE_DIR / state_file
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_state(data: dict, base_dir: str = ".", state_file: str = "workflow.json") -> Path:
    """Write a state file to .simflow/state/."""
    ensure_simflow_dir(base_dir)
    path = Path(base_dir) / STATE_DIR / state_file
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path


def init_workflow(workflow_type: str, entry_point: str, base_dir: str = ".") -> dict:
    """Initialize a new workflow state."""
    import uuid
    now = datetime.now(timezone.utc).isoformat()
    wf_id = f"wf_{uuid.uuid4().hex[:8]}"
    state = {
        "workflow_id": wf_id,
        "workflow_type": workflow_type,
        "current_stage": entry_point,
        "status": "initialized",
        "plan": None,
        "entry_point": entry_point,
        "created_at": now,
        "updated_at": now,
    }
    write_state(state, base_dir)
    write_state({}, base_dir, "stages.json")
    write_state([], base_dir, "artifacts.json")
    write_state({}, base_dir, "verification.json")
    write_state([], base_dir, "jobs.json")
    return state


def update_stage(stage_name: str, status: str, base_dir: str = ".", **kwargs: Any) -> dict:
    """Update a stage's state."""
    stages = read_state(base_dir, "stages.json")
    now = datetime.now(timezone.utc).isoformat()
    if stage_name not in stages:
        stages[stage_name] = {
            "stage_name": stage_name,
            "status": "pending",
            "agent": None,
            "inputs": [],
            "outputs": [],
            "checkpoint_id": None,
            "error_message": None,
            "started_at": now,
            "completed_at": None,
        }
    stages[stage_name]["status"] = status
    if status == "in_progress":
        stages[stage_name]["started_at"] = now
    elif status in ("completed", "failed"):
        stages[stage_name]["completed_at"] = now
    for k, v in kwargs.items():
        if k in stages[stage_name]:
            stages[stage_name][k] = v
    write_state(stages, base_dir, "stages.json")
    return stages[stage_name]
