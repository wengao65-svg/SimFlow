"""Tool: Write workflow state."""

from runtime.lib.state import write_state


def execute(params: dict) -> dict:
    base_dir = params.get("base_dir", ".")
    state_file = params.get("file", "workflow.json")
    data = params.get("data", {})
    path = write_state(data, base_dir, state_file)
    return {"status": "success", "path": str(path)}
