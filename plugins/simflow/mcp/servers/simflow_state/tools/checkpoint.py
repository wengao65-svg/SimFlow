"""Tool: create a compact SimFlow recovery checkpoint."""

from runtime.simflow_core.records import create_recovery_checkpoint
from runtime.simflow_core.state import ProjectRootError


def execute(params: dict) -> dict:
    project_root = params.get("project_root")
    if not project_root:
        return {"status": "error", "message": "project_root is required"}
    try:
        data = create_recovery_checkpoint(
            project_root,
            summary=params.get("summary", ""),
            status=params.get("status", "ready"),
            record_id=params.get("record_id"),
            run_id=params.get("run_id"),
            milestone_id=params.get("milestone_id"),
            input_refs=params.get("input_refs"),
            restart_refs=params.get("restart_refs"),
            resume_command=params.get("resume_command"),
            risk_notes=params.get("risk_notes"),
        )
    except (ProjectRootError, TypeError, ValueError) as error:
        return {"status": "error", "message": str(error)}
    return {"status": "success", "project_root": project_root, "data": data}
