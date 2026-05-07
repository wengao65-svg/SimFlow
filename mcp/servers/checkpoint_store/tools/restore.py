"""Tool: Restore from a checkpoint."""

from runtime.lib.checkpoint import restore_checkpoint
from runtime.lib.state import ProjectRootError


def _project_root(params: dict) -> str:
    return params.get("project_root") or params.get("base_dir") or "."


def execute(params: dict) -> dict:
    checkpoint_id = params.get("checkpoint_id")
    if not checkpoint_id:
        return {"status": "error", "message": "checkpoint_id is required"}
    project_root = _project_root(params)
    try:
        checkpoint = restore_checkpoint(checkpoint_id, project_root=project_root)
        return {"status": "success", "project_root": project_root, "data": checkpoint}
    except (FileNotFoundError, ProjectRootError) as e:
        return {"status": "error", "message": str(e)}
