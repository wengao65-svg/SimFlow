"""Tool: List artifacts."""

from runtime.simflow_core.artifacts import list_artifacts
from runtime.simflow_core.state import ProjectRootError


def execute(params: dict) -> dict:
    project_root = params.get("project_root")
    if not project_root:
        return {"status": "error", "message": "project_root is required for MCP artifact reads"}
    try:
        artifacts = list_artifacts(stage=params.get("stage"), project_root=project_root)
    except ProjectRootError as error:
        return {"status": "error", "message": str(error)}
    return {"status": "success", "project_root": project_root, "data": artifacts}
