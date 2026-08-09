"""Tool: Record a complete SimFlow stage failure lifecycle."""

from runtime.simflow_core.failures import record_stage_failure
from runtime.simflow_core.state import ProjectRootError


def execute(params: dict) -> dict:
    project_root = params.get("project_root")
    stage_name = params.get("stage_name")
    message = params.get("message")
    if not project_root:
        raise ProjectRootError("project_root is required for MCP write operations")
    if not stage_name or not message:
        return {"status": "error", "message": "stage_name and message are required"}
    return record_stage_failure(
        project_root=project_root,
        stage_name=stage_name,
        message=message,
        activity=params.get("activity"),
        reason_code=params.get("reason_code"),
        exception_type=params.get("exception_type"),
        traceback_text=params.get("traceback"),
        job_id=params.get("job_id"),
        partial_artifact_ids=params.get("partial_artifact_ids"),
        failure_id=params.get("failure_id"),
        experiment_id=params.get("experiment_id"),
        iteration_id=params.get("iteration_id"),
        activity_id=params.get("activity_id"),
    )
