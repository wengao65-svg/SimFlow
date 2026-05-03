"""Tool: Update stage state."""

from runtime.lib.state import update_stage


def execute(params: dict) -> dict:
    stage_name = params.get("stage_name")
    status = params.get("status")
    base_dir = params.get("base_dir", ".")
    if not stage_name or not status:
        return {"status": "error", "message": "stage_name and status are required"}
    result = update_stage(stage_name, status, base_dir)
    return {"status": "success", "data": result}
