"""Tool: Get artifact by ID."""

from runtime.simflow_core.artifacts import get_artifact
from runtime.simflow_core.state import ProjectRootError


def _project_root(params: dict) -> str:
    project_root = params.get("project_root")
    if not project_root:
        raise ProjectRootError("project_root is required for MCP artifact reads")
    return project_root


def execute(params: dict) -> dict:
    artifact_id = params.get("artifact_id")
    if not artifact_id:
        return {"status": "error", "message": "artifact_id is required"}
    try:
        project_root = _project_root(params)
        artifact = get_artifact(artifact_id, project_root=project_root)
    except ProjectRootError as error:
        return {"status": "error", "message": str(error)}
    if artifact is None:
        return {"status": "error", "message": f"Artifact not found: {artifact_id}"}
    return {"status": "success", "project_root": project_root, "data": artifact}
