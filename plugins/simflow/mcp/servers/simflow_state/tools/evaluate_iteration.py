"""Tool: Record an iteration evaluation and continuation decision."""

from runtime.simflow_core.experiment_memory import evaluate_iteration


def execute(params: dict) -> dict:
    try:
        data = evaluate_iteration(
            params["project_root"],
            session_context_id=params["session_context_id"],
            experiment_id=params["experiment_id"],
            iteration_id=params["iteration_id"],
            status=params["status"],
            criterion_results=params.get("criterion_results") or [],
            decision=params["decision"],
            next_action=params.get("next_action"),
            recovery=params.get("recovery"),
        )
    except (KeyError, ValueError) as error:
        return {"status": "error", "message": str(error)}
    return {"status": "success", "project_root": params["project_root"], "data": data}
