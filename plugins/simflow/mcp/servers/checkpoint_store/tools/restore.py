"""Tool: Restore from a checkpoint."""

from runtime.simflow_core.checkpoints import restore_checkpoint
from runtime.simflow_core.state import ProjectRootError


def _project_root(params: dict) -> str:
    project_root = params.get("project_root")
    if not project_root:
        raise ProjectRootError("project_root is required for MCP write operations")
    return project_root


def execute(params: dict) -> dict:
    checkpoint_id = params.get("checkpoint_id")
    if not checkpoint_id:
        return {"status": "error", "message": "checkpoint_id is required"}
    try:
        project_root = _project_root(params)
        checkpoint = restore_checkpoint(checkpoint_id, project_root=project_root)
        return {"status": "success", "project_root": project_root, "data": checkpoint}
    except (FileNotFoundError, ProjectRootError) as e:
        return {"status": "error", "message": str(e)}
