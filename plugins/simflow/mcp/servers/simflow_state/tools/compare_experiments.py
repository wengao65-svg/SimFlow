"""Tool: Compare tracked experiment branches."""

from runtime.simflow_core.experiment_memory import compare_experiments


def execute(params: dict) -> dict:
    try:
        return compare_experiments(params["project_root"], experiment_ids=params["experiment_ids"])
    except (KeyError, ValueError) as error:
        return {"status": "error", "message": str(error)}
