"""Tool: List checkpoints."""

from runtime.lib.checkpoint import list_checkpoints


def execute(params: dict) -> dict:
    checkpoints = list_checkpoints(params.get("base_dir", "."))
    return {"status": "success", "data": checkpoints}
