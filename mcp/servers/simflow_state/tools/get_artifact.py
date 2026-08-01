"""Tool: Get an artifact by ID."""

from runtime.simflow_core.artifacts import get_artifact
from runtime.simflow_core.state import ProjectRootError


def execute(params: dict) -> dict:
    project_root = params.get("project_root")
    if not project_root:
        return {"status": "error", "message": "project_root is required for MCP artifact reads"}
    artifact_id = params.get("artifact_id")
    if not artifact_id:
        return {"status": "error", "message": "artifact_id is required"}
    try:
        artifact = get_artifact(artifact_id, project_root=project_root)
    except ProjectRootError as error:
        return {"status": "error", "message": str(error)}
    if artifact is None:
        return {"status": "error", "message": f"Artifact not found: {artifact_id}"}
    return {"status": "success", "project_root": project_root, "data": artifact}
