"""Tool: Create a checkpoint."""

from runtime.simflow_core.checkpoints import create_checkpoint
from runtime.simflow_core.state import ProjectRootError


def execute(params: dict) -> dict:
    project_root = params.get("project_root")
    if not project_root:
        return {"status": "error", "message": "project_root is required for MCP write operations"}
    workflow_id = params.get("workflow_id")
    stage_id = params.get("stage_id")
    if not workflow_id or not stage_id:
        return {"status": "error", "message": "workflow_id and stage_id are required"}
    try:
        checkpoint = create_checkpoint(
            workflow_id=workflow_id,
            stage_id=stage_id,
            description=params.get("description", ""),
            project_root=project_root,
            status=params.get("status", "success"),
            job_id=params.get("job_id"),
        )
    except ProjectRootError as error:
        return {"status": "error", "message": str(error)}
    return {"status": "success", "project_root": project_root, "data": checkpoint}
