"""Tool: Get artifact by ID."""

from runtime.lib.artifact import get_artifact


def execute(params: dict) -> dict:
    artifact_id = params.get("artifact_id")
    if not artifact_id:
        return {"status": "error", "message": "artifact_id is required"}
    artifact = get_artifact(artifact_id, params.get("base_dir", "."))
    if artifact is None:
        return {"status": "error", "message": f"Artifact not found: {artifact_id}"}
    return {"status": "success", "data": artifact}
