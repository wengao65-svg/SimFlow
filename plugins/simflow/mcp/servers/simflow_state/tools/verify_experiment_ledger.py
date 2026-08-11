"""Tool: Verify SQLite integrity, event hashes, and evidence references."""

from runtime.simflow_core.experiment_memory import verify_experiment_ledger


def execute(params: dict) -> dict:
    try:
        return verify_experiment_ledger(
            params["project_root"],
            verify_references=params.get("verify_references", True),
        )
    except (KeyError, ValueError) as error:
        return {"status": "error", "message": str(error)}
