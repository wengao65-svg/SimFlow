"""Tool: Initialize a new workflow."""

from runtime.lib.state import ProjectRootError, init_workflow


def _project_root(params: dict) -> str:
    return params.get("project_root") or params.get("base_dir") or "."


def execute(params: dict) -> dict:
    workflow_type = params.get("workflow_type")
    entry_point = params.get("entry_point", "literature")
    project_root = _project_root(params)
    if not workflow_type:
        return {"status": "error", "message": "workflow_type is required"}
    try:
        state = init_workflow(workflow_type, entry_point, project_root=project_root)
    except ProjectRootError as error:
        return {"status": "error", "message": str(error)}
    return {"status": "success", "project_root": project_root, "data": state}
