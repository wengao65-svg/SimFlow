"""Tool: List checkpoints."""

from runtime.simflow_core.checkpoints import list_checkpoints
from runtime.simflow_core.state import ProjectRootError


def _project_root(params: dict) -> str:
    return params.get("project_root") or params.get("base_dir") or "."


def execute(params: dict) -> dict:
    project_root = _project_root(params)
    try:
        checkpoints = list_checkpoints(project_root=project_root)
    except ProjectRootError as error:
        return {"status": "error", "message": str(error)}
    return {"status": "success", "project_root": project_root, "data": checkpoints}
