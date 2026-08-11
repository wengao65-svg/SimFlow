"""Tool: validate and return a compact recovery checkpoint."""

from runtime.simflow_core.records import recover_checkpoint
from runtime.simflow_core.state import ProjectRootError


def execute(params: dict) -> dict:
    project_root = params.get("project_root")
    if not project_root:
        return {"status": "error", "message": "project_root is required"}
    try:
        data = recover_checkpoint(project_root, checkpoint_id=params.get("checkpoint_id"))
    except (ProjectRootError, FileNotFoundError, TypeError, ValueError) as error:
        return {"status": "error", "message": str(error)}
    return {"status": "success", "project_root": project_root, "data": data}
