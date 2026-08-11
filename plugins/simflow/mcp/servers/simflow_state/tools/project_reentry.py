"""Tool: Open a forward-only experiment-memory session context."""

from runtime.simflow_core.experiment_memory import project_reentry
from runtime.simflow_core.state import ProjectRootError


def execute(params: dict) -> dict:
    project_root = params.get("project_root")
    if not project_root:
        return {"status": "error", "message": "project_root is required"}
    try:
        data = project_reentry(
            project_root,
            experiment_id=params.get("experiment_id"),
            working_directory=params.get("working_directory"),
            recent_limit=params.get("recent_limit", 10),
        )
    except (ProjectRootError, ValueError) as error:
        return {"status": "error", "message": str(error)}
    return {"status": "success", "project_root": data["project_root"], "data": data}
