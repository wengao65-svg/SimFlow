"""Tool: Register an artifact."""

from runtime.simflow_core.artifacts import register_artifact
from runtime.simflow_core.state import ProjectRootError


def execute(params: dict) -> dict:
    project_root = params.get("project_root")
    if not project_root:
        return {"status": "error", "message": "project_root is required for MCP write operations"}
    name = params.get("name")
    artifact_type = params.get("type")
    stage = params.get("stage")
    if not name or not artifact_type or not stage:
        return {"status": "error", "message": "name, type, and stage are required"}
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
            metadata=params.get("metadata"),
        )
    except ProjectRootError as error:
        return {"status": "error", "message": str(error)}
    return {"status": "success", "project_root": project_root, "data": artifact}
