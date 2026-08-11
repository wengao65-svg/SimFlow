"""Tool: Write workflow state."""

from runtime.simflow_core.state import ProjectRootError, write_state


def _project_root(params: dict) -> str:
    project_root = params.get("project_root")
    if not project_root:
        raise ProjectRootError("project_root is required for MCP write operations")
    return project_root


def execute(params: dict) -> dict:
    state_file = params.get("file", "workflow.json")
    data = params.get("data", {})
    try:
        project_root = _project_root(params)
        path = write_state(
            data,
            project_root=project_root,
            state_file=state_file,
            session_context_id=params.get("session_context_id"),
            experiment_id=params.get("experiment_id"),
            iteration_id=params.get("iteration_id"),
            activity_id=params.get("activity_id"),
        )
    except ProjectRootError as error:
        return {"status": "error", "message": str(error)}
    return {"status": "success", "project_root": project_root, "path": str(path)}
