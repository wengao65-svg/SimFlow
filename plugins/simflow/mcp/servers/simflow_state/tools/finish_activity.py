"""Tool: Record the terminal outcome of an experiment activity."""

from runtime.simflow_core.experiment_memory import finish_activity


def execute(params: dict) -> dict:
    try:
        data = finish_activity(
            params["project_root"],
            session_context_id=params["session_context_id"],
            experiment_id=params["experiment_id"],
            activity_id=params["activity_id"],
            status=params["status"],
            outputs=params.get("outputs"),
            artifact_ids=params.get("artifact_ids"),
            job_ids=params.get("job_ids"),
            checkpoint_id=params.get("checkpoint_id"),
            observations=params.get("observations"),
            metrics=params.get("metrics"),
            failure=params.get("failure"),
            restart_from=params.get("restart_from"),
            next_action=params.get("next_action"),
        )
    except (KeyError, ValueError) as error:
        return {"status": "error", "message": str(error)}
    return {"status": "success", "project_root": params["project_root"], "data": data}
