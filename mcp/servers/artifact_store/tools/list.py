"""Tool: List artifacts."""

from runtime.lib.artifact import list_artifacts
from runtime.lib.state import ProjectRootError


def _project_root(params: dict) -> str:
    return params.get("project_root") or params.get("base_dir") or "."


def execute(params: dict) -> dict:
    stage = params.get("stage")
    project_root = _project_root(params)
    try:
        artifacts = list_artifacts(stage=stage, project_root=project_root)
    except ProjectRootError as error:
        return {"status": "error", "message": str(error)}
    return {"status": "success", "project_root": project_root, "data": artifacts}
