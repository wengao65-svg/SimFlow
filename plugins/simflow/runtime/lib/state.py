"""Workflow state management."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


SIMFLOW_DIR = ".simflow"
STATE_DIR = os.path.join(SIMFLOW_DIR, "state")
PLUGIN_ROOT = Path(__file__).resolve().parents[2]
CANONICAL_STATE_FILES = {
    "workflow.json": {},
    "stages.json": {},
    "artifacts.json": [],
    "checkpoints.json": [],
    "verification.json": {},
    "jobs.json": [],
    "summary.json": {"state_root": ".simflow"},
    "metadata.json": {},
}


class ProjectRootError(ValueError):
    """Raised when a SimFlow state operation targets an invalid project root."""


def get_plugin_root() -> Path:
    """Return the SimFlow plugin root used for imports and bundled assets."""
    return PLUGIN_ROOT


def is_plugin_root(path: str | Path) -> bool:
    """Return whether a path is the SimFlow plugin root/cache root."""
    root = Path(path).expanduser().resolve()
    if root == PLUGIN_ROOT:
        return True
    return (
        (root / ".codex-plugin" / "plugin.json").is_file()
        and (root / "skills" / "simflow" / "SKILL.md").is_file()
        and (root / "runtime" / "lib" / "state.py").is_file()
    )


def resolve_project_root(
    project_root: Optional[str] = None,
    base_dir: Optional[str] = None,
    *,
    reject_plugin_root: bool = True,
) -> Path:
    """Resolve the project root where .simflow state should be written.

    plugin_root is only for importing SimFlow code. project_root is the user's
    working project and is the only valid root for workflow state.
    """
    candidate = project_root if project_root is not None else base_dir
    if candidate is None:
        candidate = "."
    resolved = Path(candidate).expanduser().resolve()
    if reject_plugin_root and is_plugin_root(resolved):
        raise ProjectRootError(
            "Refusing to use the SimFlow plugin root/cache as project_root. "
            "Pass the user's current project directory as project_root."
        )
    return resolved


def get_simflow_path(base_dir: str = ".") -> Path:
    """Get the .simflow directory path."""
    return resolve_project_root(base_dir=base_dir) / SIMFLOW_DIR


def _ensure_canonical_state_files(root: Path) -> None:
    """Ensure all canonical backbone state files exist under .simflow/state/."""
    state_dir = root / STATE_DIR
    state_dir.mkdir(parents=True, exist_ok=True)
    for state_file, default_value in CANONICAL_STATE_FILES.items():
        path = state_dir / state_file
        if path.exists():
            continue
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default_value, f, indent=2, ensure_ascii=False)



def ensure_simflow_dir(base_dir: str = ".", project_root: Optional[str] = None) -> Path:
    """Ensure .simflow directory structure and canonical backbone state files exist."""
    root = resolve_project_root(project_root=project_root, base_dir=base_dir)
    sf = root / SIMFLOW_DIR
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
    _ensure_canonical_state_files(root)
    return sf


def write_report(
    content: str,
    base_dir: str = ".",
    report_file: str = "status_summary.md",
    project_root: Optional[str] = None,
) -> Path:
    """Write a report file under .simflow/reports/."""
    root = resolve_project_root(project_root=project_root, base_dir=base_dir)
    ensure_simflow_dir(project_root=str(root))
    path = root / SIMFLOW_DIR / "reports" / report_file
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def read_state(base_dir: str = ".", state_file: str = "workflow.json", project_root: Optional[str] = None) -> dict:
    """Read a state file from .simflow/state/."""
    root = resolve_project_root(project_root=project_root, base_dir=base_dir)
    path = root / STATE_DIR / state_file
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_state(
    data: dict,
    base_dir: str = ".",
    state_file: str = "workflow.json",
    project_root: Optional[str] = None,
) -> Path:
    """Write a state file to .simflow/state/."""
    root = resolve_project_root(project_root=project_root, base_dir=base_dir)
    ensure_simflow_dir(project_root=str(root))
    path = root / STATE_DIR / state_file
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path


def init_workflow(
    workflow_type: str,
    entry_point: str,
    base_dir: str = ".",
    project_root: Optional[str] = None,
) -> dict:
    """Initialize a new workflow state under .simflow/.

    .omx belongs to the host session layer and is never used as SimFlow's
    workflow state root.
    """
    import uuid
    root = resolve_project_root(project_root=project_root, base_dir=base_dir)
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
    write_state(state, project_root=str(root))
    for state_file, default_value in CANONICAL_STATE_FILES.items():
        if state_file in ("workflow.json", "summary.json"):
            continue
        write_state(default_value, project_root=str(root), state_file=state_file)
    summary = {
        "workflow_id": wf_id,
        "workflow_type": workflow_type,
        "current_stage": entry_point,
        "status": "initialized",
        "state_root": ".simflow",
        "summary_report": ".simflow/reports/status_summary.md",
        "created_at": now,
        "updated_at": now,
    }
    write_state(summary, project_root=str(root), state_file="summary.json")
    write_report(
        "\n".join([
            "# SimFlow Status Summary",
            "",
            f"- Workflow ID: {wf_id}",
            f"- Workflow type: {workflow_type}",
            f"- Current stage: {entry_point}",
            "- Status: initialized",
            "- State root: .simflow",
            "",
        ]),
        project_root=str(root),
    )
    return state


def ensure_workflow_initialized(
    workflow_type: str = "custom",
    entry_point: str = "literature",
    base_dir: str = ".",
    project_root: Optional[str] = None,
) -> dict:
    """Ensure project_root has a SimFlow workflow state tree and return state."""
    root = resolve_project_root(project_root=project_root, base_dir=base_dir)
    state = read_state(project_root=str(root))
    if state:
        ensure_simflow_dir(project_root=str(root))
        return state
    return init_workflow(workflow_type, entry_point, project_root=str(root))


def update_stage(
    stage_name: str,
    status: str,
    base_dir: str = ".",
    project_root: Optional[str] = None,
    **kwargs: Any,
) -> dict:
    """Update a stage's state."""
    root = resolve_project_root(project_root=project_root, base_dir=base_dir)
    stages = read_state(project_root=str(root), state_file="stages.json")
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
    write_state(stages, project_root=str(root), state_file="stages.json")
    return stages[stage_name]
