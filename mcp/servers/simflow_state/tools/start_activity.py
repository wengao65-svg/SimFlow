"""Tool: Record a planned or started experiment activity."""

from runtime.simflow_core.experiment_memory import start_activity


def execute(params: dict) -> dict:
    try:
        data = start_activity(
            params["project_root"],
            session_context_id=params["session_context_id"],
            experiment_id=params["experiment_id"],
            iteration_id=params.get("iteration_id"),
            objective=params["objective"],
            activity_type=params["activity_type"],
            stage=params["stage"],
            method=params.get("method"),
            software=params.get("software"),
            version=params.get("version"),
            scripts=params.get("scripts"),
            command=params.get("command"),
            inputs=params.get("inputs"),
            parameters=params.get("parameters"),
            expected_outputs=params.get("expected_outputs"),
            gate_ids=params.get("gate_ids"),
            random_seeds=params.get("random_seeds"),
            environment_ref=params.get("environment_ref"),
        )
    except (KeyError, ValueError) as error:
        return {"status": "error", "message": str(error)}
    return {"status": "success", "project_root": params["project_root"], "data": data}
