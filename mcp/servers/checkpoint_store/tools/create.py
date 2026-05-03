"""Tool: Create a checkpoint."""

from runtime.lib.checkpoint import create_checkpoint


def execute(params: dict) -> dict:
    workflow_id = params.get("workflow_id")
    stage_id = params.get("stage_id")
    description = params.get("description", "")
    if not workflow_id or not stage_id:
        return {"status": "error", "message": "workflow_id and stage_id are required"}
    checkpoint = create_checkpoint(
        workflow_id=workflow_id,
        stage_id=stage_id,
        description=description,
        base_dir=params.get("base_dir", "."),
        status=params.get("status", "success"),
        job_id=params.get("job_id"),
    )
    return {"status": "success", "data": checkpoint}
