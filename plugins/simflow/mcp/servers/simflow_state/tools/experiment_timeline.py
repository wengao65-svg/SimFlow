"""Tool: Query a paginated experiment activity timeline."""

from runtime.simflow_core.experiment_memory import experiment_timeline


def execute(params: dict) -> dict:
    try:
        data = experiment_timeline(
            params["project_root"],
            experiment_id=params["experiment_id"],
            iteration_id=params.get("iteration_id"),
            status=params.get("status"),
            offset=params.get("offset", 0),
            limit=params.get("limit", 50),
        )
    except (KeyError, ValueError) as error:
        return {"status": "error", "message": str(error)}
    return {"status": "success", "project_root": params["project_root"], "data": data}
