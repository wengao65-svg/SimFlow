"""Tool: Fork a tracked experiment into a new provenance branch."""

from runtime.simflow_core.experiment_memory import fork_experiment


def execute(params: dict) -> dict:
    try:
        data = fork_experiment(
            params["project_root"],
            session_context_id=params["session_context_id"],
            parent_experiment_id=params["parent_experiment_id"],
            title=params["title"],
            objective=params["objective"],
            root_path=params["root_path"],
            scientific_question=params.get("scientific_question"),
            hypothesis=params.get("hypothesis"),
            stage=params.get("stage"),
            recipe=params.get("recipe"),
            acceptance_criteria=params.get("acceptance_criteria"),
            baseline_refs=params.get("baseline_refs"),
            next_action=params.get("next_action"),
        )
    except (KeyError, ValueError) as error:
        return {"status": "error", "message": str(error)}
    return {"status": "success", "project_root": params["project_root"], "data": data}
