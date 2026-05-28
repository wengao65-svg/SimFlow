"""Tool: Update stage state."""

from runtime.simflow_core.state import ProjectRootError, update_stage


def _project_root(params: dict) -> str:
    project_root = params.get("project_root")
    if not project_root:
        raise ProjectRootError("project_root is required for MCP write operations")
    return project_root


def execute(params: dict) -> dict:
    stage_name = params.get("stage_name")
    status = params.get("status")
    if not stage_name or not status:
        return {"status": "error", "message": "stage_name and status are required"}
    try:
        project_root = _project_root(params)
        result = update_stage(stage_name, status, project_root=project_root)
    except ProjectRootError as error:
        return {"status": "error", "message": str(error)}
    return {"status": "success", "project_root": project_root, "data": result}
