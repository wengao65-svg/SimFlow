"""Tool: Restore from a checkpoint."""

from runtime.lib.checkpoint import restore_checkpoint


def execute(params: dict) -> dict:
    checkpoint_id = params.get("checkpoint_id")
    if not checkpoint_id:
        return {"status": "error", "message": "checkpoint_id is required"}
    try:
        checkpoint = restore_checkpoint(checkpoint_id, params.get("base_dir", "."))
        return {"status": "success", "data": checkpoint}
    except FileNotFoundError as e:
        return {"status": "error", "message": str(e)}
