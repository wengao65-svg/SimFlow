"""Tool: inspect compact SimFlow project state."""

from runtime.simflow_core.records import inspect_project
from runtime.simflow_core.state import ProjectRootError


def execute(params: dict) -> dict:
    project_root = params.get("project_root")
    if not project_root:
        return {"status": "error", "message": "project_root is required"}
    try:
        data = inspect_project(
            project_root,
            kind=params.get("kind"),
            status=params.get("status"),
            record_id=params.get("record_id"),
            run_id=params.get("run_id"),
            limit=params.get("limit", 20),
            include_legacy=params.get("include_legacy", True),
        )
    except (ProjectRootError, TypeError, ValueError) as error:
        return {"status": "error", "message": str(error)}
    return {"status": "success", "project_root": project_root, "data": data}
