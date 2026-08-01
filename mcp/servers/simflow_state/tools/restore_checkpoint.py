"""Tool: Restore from a checkpoint."""

from runtime.simflow_core.checkpoints import restore_checkpoint
from runtime.simflow_core.state import ProjectRootError


def execute(params: dict) -> dict:
    project_root = params.get("project_root")
    if not project_root:
        return {"status": "error", "message": "project_root is required for MCP write operations"}
    checkpoint_id = params.get("checkpoint_id")
    if not checkpoint_id:
        return {"status": "error", "message": "checkpoint_id is required"}
    try:
        checkpoint = restore_checkpoint(checkpoint_id, project_root=project_root)
    except (FileNotFoundError, ProjectRootError) as error:
        return {"status": "error", "message": str(error)}
    return {"status": "success", "project_root": project_root, "data": checkpoint}
