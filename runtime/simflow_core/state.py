"""Workflow state management."""

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


SIMFLOW_DIR = ".simflow"
STATE_DIR = os.path.join(SIMFLOW_DIR, "state")
BACKUPS_DIR = os.path.join(SIMFLOW_DIR, "backups")
PLUGIN_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_STATUSES = ("initialized", "in_progress", "paused", "completed", "failed")
STAGE_STATUSES = ("pending", "in_progress", "waiting", "completed", "failed", "skipped")
TERMINAL_STAGE_STATUSES = ("completed", "failed", "skipped")
VERIFICATION_STATUSES = ("pass", "warning", "fail", "pending")
CHECKPOINT_STATUSES = ("success", "partial", "failure")
CANONICAL_STATE_FILES = {
    "project.json": {},
    "workflow.json": {},
    "stages.json": {},
    "artifacts.json": [],
    "checkpoints.json": [],
    "gates.json": [],
    "lineage.json": {"artifacts": [], "links": []},
    "verification.json": [],
    "jobs.json": [],
    "summary.json": {"state_root": ".simflow"},
    "metadata.json": {},
}
CANONICAL_ARTIFACT_STAGE_DIRS = [
    "literature_review",
    "proposal",
    "modeling",
    "computation",
    "analysis_visualization",
    "writing",
]
ARTIFACT_CATEGORY_DIRS = [
    "literature",
    "models",
    "compute",
    "analysis",
    "figures",
]


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
        and (root / "runtime" / "simflow_core" / "state.py").is_file()
    )


def _normalize_path_case(resolved: Path) -> Path:
    """Normalize path case to match the actual filesystem casing.

    On case-insensitive filesystems (e.g. WSL /mnt/d/ DrvFs), Path.resolve()
    preserves the input casing rather than the disk's actual casing. This
    function uses os.path.realpath() to obtain the real disk casing and
    returns it. On case-sensitive filesystems the result is identical to
    the input.

    Issues a UserWarning when the casing is corrected, so callers can log
    the normalization for audit purposes.
    """
    try:
        real = Path(os.path.realpath(str(resolved)))
    except OSError:
        return resolved
    if str(real) != str(resolved) and real.exists():
        import warnings
        warnings.warn(
            f"project_root casing normalized: {resolved} -> {real}",
            UserWarning,
            stacklevel=3,
        )
        return real
    return resolved


def resolve_project_root(
    project_root: Optional[str] = None,
    base_dir: Optional[str] = None,
    *,
    reject_plugin_root: bool = True,
) -> Path:
    """Resolve the project root where .simflow state should be written.

    plugin_root is only for importing SimFlow code. project_root is the user's
    working project and is the only valid root for workflow state.

    Path casing is normalized to match the actual filesystem on
    case-insensitive mounts (e.g. WSL /mnt/d/), preventing state
    inconsistencies like /mnt/d/li-o-b-si vs /mnt/d/Li-O-B-Si.
    """
    candidate = project_root if project_root is not None else base_dir
    if candidate is None:
        candidate = "."
    resolved = Path(candidate).expanduser().resolve()
    resolved = _normalize_path_case(resolved)
    if reject_plugin_root and is_plugin_root(resolved):
        raise ProjectRootError(
            "Refusing to use the SimFlow plugin root/cache as project_root. "
            "Pass the user's current project directory as project_root."
        )
    return resolved


def resolve_project_path(
    path: str | Path,
    *,
    project_root: str | Path,
) -> Path:
    """Resolve a path inside project_root and reject boundary escapes."""
    root = resolve_project_root(project_root=str(project_root))
    candidate = Path(path).expanduser()
    resolved = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ProjectRootError(
            f"Refusing to resolve path outside project_root: {path}"
        ) from exc
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
        *[sf / "artifacts" / name for name in CANONICAL_ARTIFACT_STAGE_DIRS],
        *[sf / "artifacts" / name for name in ARTIFACT_CATEGORY_DIRS],
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


def read_state(base_dir: str = ".", state_file: str = "workflow.json", project_root: Optional[str] = None) -> Any:
    """Read a state file from .simflow/state/."""
    root = resolve_project_root(project_root=project_root, base_dir=base_dir)
    path = root / STATE_DIR / state_file
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_state(
    data: Any,
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


def _backup_simflow_tree(root: Path) -> Optional[Path]:
    """Create a timestamped backup of the entire .simflow tree.

    The ``backups/`` subdirectory itself is excluded to avoid recursive
    self-copy. Returns the backup path on success, or None if there was
    nothing to back up.
    """
    sf = root / SIMFLOW_DIR
    if not sf.exists():
        return None
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_root = root / BACKUPS_DIR
    backup_root.mkdir(parents=True, exist_ok=True)
    backup_path = backup_root / timestamp
    counter = 1
    while backup_path.exists():
        backup_path = backup_root / f"{timestamp}_{counter:02d}"
        counter += 1

    def _ignore_backups(directory, names):
        # Skip the backups subdirectory during copy to avoid recursion.
        if Path(directory).name == SIMFLOW_DIR and "backups" in names:
            return ["backups"]
        return []

    shutil.copytree(sf, backup_path, dirs_exist_ok=False, ignore=_ignore_backups)
    return backup_path


def init_workflow(
    workflow_type: str,
    entry_point: str,
    base_dir: str = ".",
    project_root: Optional[str] = None,
    *,
    force: bool = False,
) -> dict:
    """Initialize a new workflow state under .simflow/.

    By default this function is idempotent: if a workflow state already exists
    under ``project_root/.simflow/state/workflow.json`` it is preserved and the
    existing state is returned unchanged. Pass ``force=True`` to back up the
    existing ``.simflow`` tree to ``.simflow/backups/<timestamp>`` and recreate
    the canonical backbone state files.

    ``.omx`` belongs to the host session layer and is never used as SimFlow's
    workflow state root.
    """
    import uuid
    root = resolve_project_root(project_root=project_root, base_dir=base_dir)
    existing_state = read_state(project_root=str(root))
    if existing_state and not force:
        ensure_simflow_dir(project_root=str(root))
        return existing_state

    backup_path: Optional[Path] = None
    if existing_state and force:
        backup_path = _backup_simflow_tree(root)

    now = datetime.now(timezone.utc).isoformat()
    wf_id = existing_state.get("workflow_id") if existing_state else f"wf_{uuid.uuid4().hex[:8]}"
    state = {
        "workflow_id": wf_id,
        "workflow_type": workflow_type,
        "current_stage": entry_point,
        "status": "initialized",
        "plan": None,
        "entry_point": entry_point,
        "created_at": existing_state.get("created_at", now) if existing_state else now,
        "updated_at": now,
    }
    if backup_path is not None:
        state["_simflow_backup_path"] = str(backup_path)
    write_state(state, project_root=str(root))
    for state_file, default_value in CANONICAL_STATE_FILES.items():
        if state_file in ("workflow.json", "summary.json", "project.json"):
            continue
        if existing_state and not force:
            continue
        write_state(default_value, project_root=str(root), state_file=state_file)
    project = {
        "project_root": str(root),
        "state_root": ".simflow",
        "workflow_id": wf_id,
        "created_at": existing_state.get("created_at", now) if existing_state else now,
        "updated_at": now,
    }
    write_state(project, project_root=str(root), state_file="project.json")
    summary = {
        "workflow_id": wf_id,
        "workflow_type": workflow_type,
        "current_stage": entry_point,
        "status": "initialized",
        "state_root": ".simflow",
        "summary_report": ".simflow/reports/status_summary.md",
        "created_at": existing_state.get("created_at", now) if existing_state else now,
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
    entry_point: str = "literature_review",
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


def _build_status_summary_md(root: Path) -> str:
    """Build a human-readable status summary from current state files."""
    wf = read_state(project_root=str(root), state_file="workflow.json") or {}
    summary = read_state(project_root=str(root), state_file="summary.json") or {}
    stages = read_state(project_root=str(root), state_file="stages.json") or {}
    artifacts = read_state(project_root=str(root), state_file="artifacts.json")
    artifact_count = len(artifacts) if isinstance(artifacts, list) else 0
    checkpoints = read_state(project_root=str(root), state_file="checkpoints.json")
    checkpoint_count = len(checkpoints) if isinstance(checkpoints, list) else 0
    gates = read_state(project_root=str(root), state_file="gates.json")
    gate_count = len(gates) if isinstance(gates, list) else 0
    jobs = read_state(project_root=str(root), state_file="jobs.json")
    job_count = len(jobs) if isinstance(jobs, list) else 0

    lines = [
        "# SimFlow Status Summary",
        "",
        f"- Workflow ID: {wf.get('workflow_id', 'unknown')}",
        f"- Workflow type: {wf.get('workflow_type', 'unknown')}",
        f"- Current stage: {wf.get('current_stage', 'unknown')}",
        f"- Status: {wf.get('status', 'unknown')}",
        f"- State root: .simflow",
        f"- Updated: {wf.get('updated_at', 'unknown')}",
        "",
        "## Stage Status",
        "",
    ]
    if isinstance(stages, dict) and stages:
        for stage_name in CANONICAL_ARTIFACT_STAGE_DIRS:
            stage = stages.get(stage_name)
            if isinstance(stage, dict):
                lines.append(f"- {stage_name}: {stage.get('status', 'pending')}")
        # Also include any non-canonical stages that were declared
        for stage_name, stage in sorted(stages.items()):
            if stage_name not in CANONICAL_ARTIFACT_STAGE_DIRS and isinstance(stage, dict):
                lines.append(f"- {stage_name}: {stage.get('status', 'pending')}")
    else:
        lines.append("(no stages declared)")

    lines.extend([
        "",
        "## Counts",
        "",
        f"- Artifacts: {artifact_count}",
        f"- Checkpoints: {checkpoint_count}",
        f"- Gates: {gate_count}",
        f"- Jobs: {job_count}",
        "",
    ])
    return "\n".join(lines)


def touch_workflow(
    project_root: str,
    *,
    current_stage: Optional[str] = None,
    status: Optional[str] = None,
) -> None:
    """Refresh workflow.json, summary.json, and status_summary.md timestamps.

    Call this after any meaningful state change (checkpoint creation, artifact
    registration, evidence recording, stage update) to keep the top-level
    state files current. This prevents cross-session amnesia where
    summary.json.updated_at falls days behind the actual latest work.

    Args:
        project_root: The project root path.
        current_stage: If provided, update workflow.json.current_stage.
        status: If provided, update workflow.json.status.
    """
    root = resolve_project_root(project_root=project_root)
    now = datetime.now(timezone.utc).isoformat()

    # Update workflow.json
    wf = read_state(project_root=str(root), state_file="workflow.json") or {}
    wf["updated_at"] = now
    if current_stage is not None:
        wf["current_stage"] = current_stage
    if status is not None:
        wf["status"] = status
    write_state(wf, project_root=str(root), state_file="workflow.json")

    # Update summary.json
    summary = read_state(project_root=str(root), state_file="summary.json") or {}
    summary["updated_at"] = now
    if current_stage is not None:
        summary["current_stage"] = current_stage
    if status is not None:
        summary["status"] = status
    if "workflow_id" not in summary and "workflow_id" in wf:
        summary["workflow_id"] = wf["workflow_id"]
    if "workflow_type" not in summary and "workflow_type" in wf:
        summary["workflow_type"] = wf["workflow_type"]
    summary.setdefault("state_root", ".simflow")
    summary.setdefault("summary_report", ".simflow/reports/status_summary.md")
    write_state(summary, project_root=str(root), state_file="summary.json")

    # Regenerate status_summary.md
    report_content = _build_status_summary_md(root)
    write_report(report_content, project_root=str(root))


def update_stage(
    stage_name: str,
    status: str,
    base_dir: str = ".",
    project_root: Optional[str] = None,
    **kwargs: Any,
) -> dict:
    """Update a stage's state."""
    normalized_status = str(status).strip().lower()
    if normalized_status not in STAGE_STATUSES:
        raise ValueError(f"Unsupported stage status: {status}")
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
            "failure_checkpoint_id": None,
            "last_success_checkpoint_id": None,
            "error_message": None,
            "error_report_artifact_id": None,
            "failure_id": None,
            "started_at": None,
            "completed_at": None,
        }
    stages[stage_name]["status"] = normalized_status
    if normalized_status == "in_progress":
        stages[stage_name]["started_at"] = now
        stages[stage_name]["completed_at"] = None
        stages[stage_name]["error_message"] = None
        stages[stage_name]["error_report_artifact_id"] = None
        stages[stage_name]["failure_id"] = None
    elif normalized_status in TERMINAL_STAGE_STATUSES:
        stages[stage_name]["completed_at"] = now
    else:
        stages[stage_name]["completed_at"] = None
    for k, v in kwargs.items():
        if k in stages[stage_name]:
            stages[stage_name][k] = v
    if normalized_status == "completed":
        stages[stage_name]["error_message"] = None
    write_state(stages, project_root=str(root), state_file="stages.json")
    # Auto-refresh workflow.json/summary.json/status_summary.md
    touch_workflow(
        str(root),
        current_stage=stage_name if normalized_status == "in_progress" else None,
    )
    # P3.3: Auto-create verification record when stage is marked completed
    if normalized_status == "completed":
        try:
            from .verification import record_stage_completion_verification
            checkpoint_id = stages[stage_name].get("checkpoint_id")
            record_stage_completion_verification(
                stage_name, str(root), checkpoint_id=checkpoint_id,
            )
        except Exception:
            pass  # Don't fail update_stage if verification recording fails
    return stages[stage_name]
