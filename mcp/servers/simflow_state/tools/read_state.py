"""Tool: Read workflow state."""

from runtime.lib.state import ProjectRootError, read_state


def _project_root(params: dict) -> str:
    return params.get("project_root") or params.get("base_dir") or "."


def execute(params: dict) -> dict:
    project_root = _project_root(params)
    state_file = params.get("file", "workflow.json")
    try:
        data = read_state(project_root=project_root, state_file=state_file)
    except ProjectRootError as error:
        return {"status": "error", "message": str(error)}
    return {"status": "success", "project_root": project_root, "data": data}
