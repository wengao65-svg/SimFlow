"""Tool: List artifacts."""

from runtime.simflow_core.artifacts import list_artifacts
from runtime.simflow_core.state import ProjectRootError


def _project_root(params: dict) -> str:
    project_root = params.get("project_root")
    if not project_root:
        raise ProjectRootError("project_root is required for MCP artifact reads")
    return project_root


def execute(params: dict) -> dict:
    stage = params.get("stage")
    try:
        project_root = _project_root(params)
        artifacts = list_artifacts(stage=stage, project_root=project_root)
    except ProjectRootError as error:
        return {"status": "error", "message": str(error)}
    return {"status": "success", "project_root": project_root, "data": artifacts}
