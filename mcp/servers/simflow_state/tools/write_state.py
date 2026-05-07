"""Tool: Write workflow state."""

from runtime.lib.state import ProjectRootError, write_state


def _project_root(params: dict) -> str:
    return params.get("project_root") or params.get("base_dir") or "."


def execute(params: dict) -> dict:
    project_root = _project_root(params)
    state_file = params.get("file", "workflow.json")
    data = params.get("data", {})
    try:
        path = write_state(data, project_root=project_root, state_file=state_file)
    except ProjectRootError as error:
        return {"status": "error", "message": str(error)}
    return {"status": "success", "project_root": project_root, "path": str(path)}
