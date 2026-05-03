"""Tool: List artifacts."""

from runtime.lib.artifact import list_artifacts


def execute(params: dict) -> dict:
    stage = params.get("stage")
    base_dir = params.get("base_dir", ".")
    artifacts = list_artifacts(stage=stage, base_dir=base_dir)
    return {"status": "success", "data": artifacts}
