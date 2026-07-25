"""Tool: Initialize a new workflow (idempotent by default)."""

from runtime.simflow_core.state import ProjectRootError, init_workflow

CANONICAL_ENTRY_POINTS = {
    "literature_review",
    "proposal",
    "modeling",
    "computation",
    "analysis_visualization",
    "writing",
}


def _project_root(params: dict) -> str:
    project_root = params.get("project_root")
    if not project_root:
        raise ProjectRootError("project_root is required for MCP write operations")
    return project_root


def execute(params: dict) -> dict:
    """Idempotently initialize a SimFlow workflow state tree.

    If a workflow already exists under ``project_root/.simflow/state/workflow.json``
    it is returned unchanged. Pass ``force=true`` to back up the existing tree
    to ``.simflow/backups/<timestamp>/`` and recreate canonical state files.
    """
    workflow_type = params.get("workflow_type")
    entry_point = params.get("entry_point", "literature_review")
    force = bool(params.get("force", False))
    if not workflow_type:
        return {"status": "error", "message": "workflow_type is required"}
    if entry_point not in CANONICAL_ENTRY_POINTS:
        allowed = ", ".join(sorted(CANONICAL_ENTRY_POINTS))
        return {"status": "error", "message": f"entry_point must be a canonical stage: {allowed}"}
    try:
        project_root = _project_root(params)
        state = init_workflow(workflow_type, entry_point, project_root=project_root, force=force)
    except ProjectRootError as error:
        return {"status": "error", "message": str(error)}
    response = {"status": "success", "project_root": project_root, "data": state}
    if force and state.get("_simflow_backup_path"):
        response["backup_path"] = state["_simflow_backup_path"]
    return response
