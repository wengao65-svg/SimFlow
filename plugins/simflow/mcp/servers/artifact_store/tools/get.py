"""Tool: Get artifact by ID."""

from runtime.lib.artifact import get_artifact
from runtime.lib.state import ProjectRootError


def _project_root(params: dict) -> str:
    return params.get("project_root") or params.get("base_dir") or "."


def execute(params: dict) -> dict:
    artifact_id = params.get("artifact_id")
    if not artifact_id:
        return {"status": "error", "message": "artifact_id is required"}
    project_root = _project_root(params)
    try:
        artifact = get_artifact(artifact_id, project_root=project_root)
    except ProjectRootError as error:
        return {"status": "error", "message": str(error)}
    if artifact is None:
        return {"status": "error", "message": f"Artifact not found: {artifact_id}"}
    return {"status": "success", "project_root": project_root, "data": artifact}
