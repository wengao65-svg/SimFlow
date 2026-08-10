"""Tool: Resume a paused experiment."""

from runtime.simflow_core.experiment_memory import resume_experiment


def execute(params: dict) -> dict:
    try:
        data = resume_experiment(
            params["project_root"],
            session_context_id=params["session_context_id"],
            experiment_id=params["experiment_id"],
            next_action=params.get("next_action"),
        )
    except (KeyError, ValueError) as error:
        return {"status": "error", "message": str(error)}
    return {"status": "success", "project_root": params["project_root"], "data": data}
