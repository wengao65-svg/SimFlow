"""Tool: Register an artifact."""

from runtime.simflow_core.artifacts import register_artifact
from runtime.simflow_core.state import ProjectRootError


def _project_root(params: dict) -> str:
    project_root = params.get("project_root")
    if not project_root:
        raise ProjectRootError("project_root is required for MCP write operations")
    return project_root


def execute(params: dict) -> dict:
    name = params.get("name")
    artifact_type = params.get("type")
    stage = params.get("stage")
    if not name or not artifact_type or not stage:
        return {"status": "error", "message": "name, type, and stage are required"}
    try:
        project_root = _project_root(params)
        artifact = register_artifact(
            name=name,
            artifact_type=artifact_type,
            stage=stage,
            project_root=project_root,
            path=params.get("path"),
            parent_artifacts=params.get("parent_artifacts"),
            parameters=params.get("parameters"),
            software=params.get("software"),
            metadata=params.get("metadata"),
        )
    except ProjectRootError as error:
        return {"status": "error", "message": str(error)}
    return {"status": "success", "project_root": project_root, "data": artifact}
