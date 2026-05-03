"""Tool: Initialize a new workflow."""

from runtime.lib.state import init_workflow


def execute(params: dict) -> dict:
    workflow_type = params.get("workflow_type")
    entry_point = params.get("entry_point", "literature")
    base_dir = params.get("base_dir", ".")
    if not workflow_type:
        return {"status": "error", "message": "workflow_type is required"}
    state = init_workflow(workflow_type, entry_point, base_dir)
    return {"status": "success", "data": state}
