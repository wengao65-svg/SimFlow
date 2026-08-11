"""Tool: Begin an iteration within a tracked experiment."""

from runtime.simflow_core.experiment_memory import begin_iteration


def execute(params: dict) -> dict:
    try:
        data = begin_iteration(
            params["project_root"],
            session_context_id=params["session_context_id"],
            experiment_id=params["experiment_id"],
            objective=params["objective"],
            acceptance_criteria=params.get("acceptance_criteria") or [],
            parent_iteration_id=params.get("parent_iteration_id"),
            inputs=params.get("inputs"),
            next_action=params.get("next_action"),
        )
    except (KeyError, ValueError) as error:
        return {"status": "error", "message": str(error)}
    return {"status": "success", "project_root": params["project_root"], "data": data}
