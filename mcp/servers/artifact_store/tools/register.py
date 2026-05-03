"""Tool: Register an artifact."""

from runtime.lib.artifact import register_artifact


def execute(params: dict) -> dict:
    name = params.get("name")
    artifact_type = params.get("type")
    stage = params.get("stage")
    if not name or not artifact_type or not stage:
        return {"status": "error", "message": "name, type, and stage are required"}
    artifact = register_artifact(
        name=name,
        artifact_type=artifact_type,
        stage=stage,
        base_dir=params.get("base_dir", "."),
        path=params.get("path"),
        parent_artifacts=params.get("parent_artifacts"),
        parameters=params.get("parameters"),
        software=params.get("software"),
    )
    return {"status": "success", "data": artifact}
