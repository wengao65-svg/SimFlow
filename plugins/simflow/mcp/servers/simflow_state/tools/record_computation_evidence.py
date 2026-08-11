"""Tool: Record user-provided computation evidence for tracked-only tools."""

from runtime.simflow_core.state import ProjectRootError
from runtime.simflow_helpers.computation.evidence_intake import record_computation_evidence


def _project_root(params: dict) -> str:
    project_root = params.get("project_root")
    if not project_root:
        raise ProjectRootError("project_root is required for MCP write operations")
    return project_root


def execute(params: dict) -> dict:
    try:
        project_root = _project_root(params)
        result = record_computation_evidence(
            project_root,
            params=params.get("evidence_params") or {},
            dry_run=bool(params.get("dry_run", False)),
            session_context_id=params.get("session_context_id"),
            experiment_id=params.get("experiment_id"),
            iteration_id=params.get("iteration_id"),
            activity_id=params.get("activity_id"),
        )
    except ProjectRootError as error:
        return {"status": "error", "message": str(error)}
    except FileNotFoundError as error:
        return {"status": "error", "message": str(error), "code": "missing_proposal_artifacts"}
    return {"status": result.get("status", "success"), "project_root": project_root, "data": result}
