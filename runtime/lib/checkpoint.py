"""Checkpoint management for workflow recovery."""

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


CHECKPOINTS_DIR = ".simflow/checkpoints"
STATE_DIR = ".simflow/state"


def create_checkpoint(
    workflow_id: str,
    stage_id: str,
    description: str,
    base_dir: str = ".",
    status: str = "success",
    job_id: Optional[str] = None,
) -> dict:
    """Create a workflow checkpoint."""
    import re
    ckpt_dir = Path(base_dir) / CHECKPOINTS_DIR
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    # Generate checkpoint ID
    existing = list(ckpt_dir.glob("ckpt_*.json"))
    num = len(existing) + 1
    safe_stage = re.sub(r"[^a-z0-9]", "_", stage_id.lower())
    ckpt_id = f"ckpt_{num:03d}_{safe_stage}"

    now = datetime.now(timezone.utc).isoformat()

    # Snapshot current state
    state_snapshot = {}
    state_path = Path(base_dir) / STATE_DIR
    if state_path.exists():
        for f in state_path.glob("*.json"):
            with open(f, "r", encoding="utf-8") as fh:
                state_snapshot[f.name] = json.load(fh)

    # Snapshot artifact versions
    artifacts_path = state_path / "artifacts.json"
    artifact_versions = {}
    if artifacts_path.exists():
        with open(artifacts_path, "r", encoding="utf-8") as f:
            arts = json.load(f)
            for a in arts:
                artifact_versions[a["artifact_id"]] = a["version"]

    checkpoint = {
        "checkpoint_id": ckpt_id,
        "workflow_id": workflow_id,
        "stage_id": stage_id,
        "job_id": job_id,
        "description": description,
        "state_snapshot": state_snapshot,
        "artifact_versions": artifact_versions,
        "status": status,
        "created_at": now,
    }

    ckpt_file = ckpt_dir / f"{ckpt_id}.json"
    with open(ckpt_file, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, indent=2, ensure_ascii=False)

    registry_path = Path(base_dir) / STATE_DIR / "checkpoints.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry = []
    if registry_path.exists():
        with open(registry_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
            if isinstance(loaded, list):
                registry = loaded
    registry.append({
        "checkpoint_id": ckpt_id,
        "workflow_id": workflow_id,
        "stage_id": stage_id,
        "job_id": job_id,
        "status": status,
        "path": str(Path(CHECKPOINTS_DIR) / f"{ckpt_id}.json"),
        "created_at": now,
    })
    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)

    return checkpoint


def list_checkpoints(base_dir: str = ".") -> list:
    """List all checkpoints."""
    ckpt_dir = Path(base_dir) / CHECKPOINTS_DIR
    if not ckpt_dir.exists():
        return []
    checkpoints = []
    for f in sorted(ckpt_dir.glob("ckpt_*.json")):
        with open(f, "r", encoding="utf-8") as fh:
            checkpoints.append(json.load(fh))
    return checkpoints


def restore_checkpoint(checkpoint_id: str, base_dir: str = ".") -> dict:
    """Restore workflow state from a checkpoint."""
    ckpt_file = Path(base_dir) / CHECKPOINTS_DIR / f"{checkpoint_id}.json"
    if not ckpt_file.exists():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_id}")

    with open(ckpt_file, "r", encoding="utf-8") as f:
        checkpoint = json.load(f)

    # Restore state files
    state_dir = Path(base_dir) / STATE_DIR
    state_dir.mkdir(parents=True, exist_ok=True)
    for name, data in checkpoint["state_snapshot"].items():
        with open(state_dir / name, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    return checkpoint


def get_latest_checkpoint(base_dir: str = ".") -> Optional[dict]:
    """Get the most recent checkpoint."""
    checkpoints = list_checkpoints(base_dir)
    if not checkpoints:
        return None
    return checkpoints[-1]
