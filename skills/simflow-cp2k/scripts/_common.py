"""Shared I/O helpers for the simflow-cp2k skill wrappers."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


SIMFLOW_ROOT = Path(__file__).resolve().parents[3]
if str(SIMFLOW_ROOT) not in sys.path:
    sys.path.insert(0, str(SIMFLOW_ROOT))

from runtime.lib.artifact import register_artifact
from runtime.lib.checkpoint import create_checkpoint
from runtime.lib.state import ensure_workflow_initialized, resolve_project_root, update_stage, write_state


def ensure_cp2k_project(project_root: str, stage: str) -> tuple[Path, dict[str, Any]]:
    """Resolve project_root and ensure `.simflow/` exists there."""
    root = resolve_project_root(project_root=project_root)
    state = ensure_workflow_initialized("cp2k", stage, project_root=str(root))
    return root, state


def write_json_verified(root: Path, relative_path: str, data: dict[str, Any]) -> str:
    """Write JSON under project_root and re-read it for verification."""
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    json.loads(path.read_text(encoding="utf-8"))
    return relative_path


def register_report(root: Path, stage: str, task: str, name: str, relative_path: str, artifact_type: str = "report") -> dict[str, Any]:
    """Register a report-like artifact for the CP2K skill."""
    return register_artifact(
        name=name,
        artifact_type=artifact_type,
        stage=stage,
        path=relative_path,
        project_root=str(root),
        parameters={"task": task},
        software="cp2k",
    )


def finalize_stage(
    root: Path,
    state: dict[str, Any],
    stage: str,
    task: str,
    written_files: dict[str, str],
    status: str,
    description: str,
) -> dict[str, Any]:
    """Create checkpoint, update stage state, and store CP2K stage metadata."""
    checkpoint = create_checkpoint(
        workflow_id=state.get("workflow_id", "wf_cp2k"),
        stage_id=stage,
        description=description,
        project_root=str(root),
        status=status,
    )
    update_stage(
        stage,
        "completed" if status == "success" else "failed",
        project_root=str(root),
        outputs=list(written_files.values()),
        checkpoint_id=checkpoint["checkpoint_id"],
    )
    write_state(
        {
            "latest_task": task,
            "latest_stage": stage,
            "latest_checkpoint": checkpoint["checkpoint_id"],
            "written_files": written_files,
            "status": status,
        },
        project_root=str(root),
        state_file="cp2k.json",
    )
    return checkpoint

