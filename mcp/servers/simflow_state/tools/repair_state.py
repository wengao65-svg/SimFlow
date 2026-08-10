"""Tool: Audit or conservatively repair SimFlow state."""

from runtime.simflow_core.repair import audit_state, apply_state_repair
from runtime.simflow_core.state import ProjectRootError


def execute(params: dict) -> dict:
    project_root = params.get("project_root")
    if not project_root:
        raise ProjectRootError("project_root is required for state repair")
    mode = str(params.get("mode", "audit")).strip().lower()
    threshold = float(params.get("min_confidence", 0.81))
    if mode == "audit":
        return {"status": "success", "data": audit_state(project_root, min_confidence=threshold)}
    if mode == "apply":
        return {"status": "success", "data": apply_state_repair(
            project_root,
            min_confidence=threshold,
            session_context_id=params.get("session_context_id"),
            experiment_id=params.get("experiment_id"),
            iteration_id=params.get("iteration_id"),
            activity_id=params.get("activity_id"),
        )}
    return {"status": "error", "message": "mode must be 'audit' or 'apply'"}
