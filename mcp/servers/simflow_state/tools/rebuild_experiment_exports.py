"""Tool: Rebuild derived JSON/JSONL/Markdown experiment views."""

from runtime.simflow_core.experiment_memory import rebuild_experiment_exports


def execute(params: dict) -> dict:
    try:
        return rebuild_experiment_exports(
            params["project_root"],
            session_context_id=params["session_context_id"],
            experiment_id=params["experiment_id"],
            activity_id=params["activity_id"],
            iteration_id=params.get("iteration_id"),
        )
    except (KeyError, ValueError) as error:
        return {"status": "error", "message": str(error)}
