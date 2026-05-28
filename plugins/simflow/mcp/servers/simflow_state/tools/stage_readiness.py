"""Tool: Build a read-only readiness diagnostic for one SimFlow stage."""

from runtime.simflow_core.readiness import build_stage_readiness
from runtime.simflow_core.state import ProjectRootError


def _project_root(params: dict) -> str:
    project_root = params.get("project_root")
    if not project_root:
        raise ProjectRootError("project_root is required for MCP read operations")
    return project_root


def execute(params: dict) -> dict:
    try:
        project_root = _project_root(params)
        readiness = build_stage_readiness(project_root, stage=params.get("stage"))
    except ProjectRootError as error:
        return {"status": "error", "message": str(error)}
    return {"status": "success", "project_root": project_root, "data": readiness}
