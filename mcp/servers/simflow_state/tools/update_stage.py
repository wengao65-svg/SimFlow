"""Tool: Update stage state."""

from runtime.lib.state import ProjectRootError, update_stage


def _project_root(params: dict) -> str:
    return params.get("project_root") or params.get("base_dir") or "."


def execute(params: dict) -> dict:
    stage_name = params.get("stage_name")
    status = params.get("status")
    project_root = _project_root(params)
    if not stage_name or not status:
        return {"status": "error", "message": "stage_name and status are required"}
    try:
        result = update_stage(stage_name, status, project_root=project_root)
    except ProjectRootError as error:
        return {"status": "error", "message": str(error)}
    return {"status": "success", "project_root": project_root, "data": result}
