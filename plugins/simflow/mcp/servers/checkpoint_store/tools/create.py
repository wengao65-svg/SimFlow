"""Tool: Create a checkpoint."""

from runtime.lib.checkpoint import create_checkpoint
from runtime.lib.state import ProjectRootError


def _project_root(params: dict) -> str:
    return params.get("project_root") or params.get("base_dir") or "."


def execute(params: dict) -> dict:
    workflow_id = params.get("workflow_id")
    stage_id = params.get("stage_id")
    description = params.get("description", "")
    if not workflow_id or not stage_id:
        return {"status": "error", "message": "workflow_id and stage_id are required"}
    project_root = _project_root(params)
    try:
        checkpoint = create_checkpoint(
            workflow_id=workflow_id,
            stage_id=stage_id,
            description=description,
            project_root=project_root,
            status=params.get("status", "success"),
            job_id=params.get("job_id"),
        )
    except ProjectRootError as error:
        return {"status": "error", "message": str(error)}
    return {"status": "success", "project_root": project_root, "data": checkpoint}
