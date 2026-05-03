"""Tool: Read workflow state."""

from runtime.lib.state import read_state


def execute(params: dict) -> dict:
    base_dir = params.get("base_dir", ".")
    state_file = params.get("file", "workflow.json")
    data = read_state(base_dir, state_file)
    return {"status": "success", "data": data}
