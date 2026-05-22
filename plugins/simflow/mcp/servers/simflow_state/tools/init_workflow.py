"""Tool: Initialize a new workflow."""

from runtime.lib.state import ProjectRootError, init_workflow


def _project_root(params: dict) -> str:
    project_root = params.get("project_root")
    if not project_root:
        raise ProjectRootError("project_root is required for MCP write operations")
    return project_root


def execute(params: dict) -> dict:
    workflow_type = params.get("workflow_type")
    entry_point = params.get("entry_point", "literature")
    if not workflow_type:
        return {"status": "error", "message": "workflow_type is required"}
    try:
        project_root = _project_root(params)
        state = init_workflow(workflow_type, entry_point, project_root=project_root)
    except ProjectRootError as error:
        return {"status": "error", "message": str(error)}
    return {"status": "success", "project_root": project_root, "data": state}
