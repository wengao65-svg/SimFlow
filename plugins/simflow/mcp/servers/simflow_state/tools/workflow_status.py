"""Tool: Build a read-only SimFlow project status summary."""

from runtime.simflow_core.state import ProjectRootError
from runtime.simflow_core.status import build_project_status


def _project_root(params: dict) -> str:
    project_root = params.get("project_root")
    if not project_root:
        raise ProjectRootError("project_root is required for MCP read operations")
    return project_root


def execute(params: dict) -> dict:
    try:
        project_root = _project_root(params)
        summary = build_project_status(project_root)
    except ProjectRootError as error:
        return {"status": "error", "message": str(error)}
    return {"status": "success", "project_root": project_root, "data": summary}
