"""Tool: Begin a forward-only tracked experiment."""

from runtime.simflow_core.experiment_memory import begin_experiment


def execute(params: dict) -> dict:
    try:
        data = begin_experiment(
            params["project_root"],
            session_context_id=params["session_context_id"],
            title=params["title"],
            objective=params["objective"],
            stage=params["stage"],
            root_path=params["root_path"],
            recipe=params.get("recipe"),
            acceptance_criteria=params.get("acceptance_criteria"),
            next_action=params.get("next_action"),
            scientific_question=params.get("scientific_question"),
            hypothesis=params.get("hypothesis"),
            tags=params.get("tags"),
            parent_experiment_ids=params.get("parent_experiment_ids"),
            baseline_refs=params.get("baseline_refs"),
        )
    except (KeyError, ValueError) as error:
        return {"status": "error", "message": str(error)}
    return {"status": "success", "project_root": params["project_root"], "data": data}
