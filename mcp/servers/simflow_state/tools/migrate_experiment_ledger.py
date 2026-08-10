"""Tool: Explicitly migrate the structured v1 ledger, never host transcripts."""

from runtime.simflow_core.experiment_memory import migrate_experiment_ledger


def execute(params: dict) -> dict:
    try:
        return migrate_experiment_ledger(params["project_root"], confirm=params.get("confirm", False))
    except (KeyError, ValueError) as error:
        return {"status": "error", "message": str(error)}
