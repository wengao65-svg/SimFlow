"""Tool: Register an artifact."""

from runtime.lib.artifact import register_artifact
from runtime.lib.state import ProjectRootError


def _project_root(params: dict) -> str:
    return params.get("project_root") or params.get("base_dir") or "."


def execute(params: dict) -> dict:
    name = params.get("name")
    artifact_type = params.get("type")
    stage = params.get("stage")
    if not name or not artifact_type or not stage:
        return {"status": "error", "message": "name, type, and stage are required"}
    project_root = _project_root(params)
    try:
        artifact = register_artifact(
            name=name,
            artifact_type=artifact_type,
            stage=stage,
            project_root=project_root,
            path=params.get("path"),
            parent_artifacts=params.get("parent_artifacts"),
            parameters=params.get("parameters"),
            software=params.get("software"),
        )
    except ProjectRootError as error:
        return {"status": "error", "message": str(error)}
    return {"status": "success", "project_root": project_root, "data": artifact}
