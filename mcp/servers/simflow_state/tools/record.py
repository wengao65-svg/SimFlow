"""Tool: append one operational record or one scientific notebook entry."""

import uuid

from runtime.simflow_core.migration import MigrationError, apply_migration
from runtime.simflow_core.experiment_notebook import (
    ExperimentNotebookError,
    append_experiment_entry,
    create_experiment,
)
from runtime.simflow_core.project_summary import rebuild_project_summary
from runtime.simflow_core.records import record_event
from runtime.simflow_core.state import ProjectRootError, resolve_project_path, resolve_project_root


_PAYLOAD_KEYS = {
    "experiment": {"title", "research_question", "scope_paths", "tags", "status", "next_action"},
    "attempt": {"attempt_id", "method", "parameters", "acceptance_criteria", "software", "status", "evidence", "next_action", "details"},
    "observation": {"attempt_id", "status", "evidence", "next_action", "details", "uncertainty"},
    "decision": {"attempt_id", "status", "outcome", "rationale", "alternatives", "evidence", "next_action", "details"},
    "material_action": {
        "attempt_id", "status", "operation", "material_action_id", "targets", "reason",
        "selection_criteria", "recoverability", "outcome", "actual_scope", "evidence",
        "next_action", "details",
    },
    "recovery": {"attempt_id", "status", "checkpoint_id", "decision", "evidence", "next_action", "details"},
}
_EXPERIMENT_TOP_LEVEL_KEYS = {
    "project_root", "channel", "entry_type", "action", "summary", "experiment_id",
    "parent_entry_ids", "runtime_record_ids", "idempotency_key", "payload",
}
_EXPERIMENT_ONLY_KEYS = {"entry_type", "action", "parent_entry_ids", "runtime_record_ids", "payload"}


def _experiment_record(params: dict) -> dict:
    unknown_top_level = sorted(set(params) - _EXPERIMENT_TOP_LEVEL_KEYS)
    if unknown_top_level:
        raise ExperimentNotebookError(f"Unsupported experiment record fields: {unknown_top_level}")
    entry_type = params.get("entry_type")
    if entry_type not in _PAYLOAD_KEYS:
        raise ExperimentNotebookError(f"Unsupported experiment entry_type: {entry_type}")
    payload = params.get("payload")
    if not isinstance(payload, dict):
        raise ExperimentNotebookError("experiment record payload must be an object")
    unknown = sorted(set(payload) - _PAYLOAD_KEYS[entry_type])
    if unknown:
        raise ExperimentNotebookError(f"Unsupported {entry_type} payload fields: {unknown}")
    action = str(params.get("action") or "").strip()
    if not action:
        raise ExperimentNotebookError("action is required for experiment records")

    project_root = params["project_root"]
    if entry_type == "experiment" and action == "create":
        missing = [field for field in ("title", "research_question", "scope_paths") if not payload.get(field)]
        if missing:
            raise ExperimentNotebookError(f"experiment/create missing fields: {missing}")
        created = create_experiment(
            project_root,
            experiment_id=params.get("experiment_id"),
            title=payload["title"],
            research_question=payload["research_question"],
            scope_paths=payload["scope_paths"],
            tags=payload.get("tags"),
            summary=params["summary"],
            idempotency_key=params.get("idempotency_key"),
        )
        rebuild_project_summary(project_root)
        return {
            **created,
            "path": str(created["path"].relative_to(created["path"].parents[2])),
        }

    experiment_id = params.get("experiment_id")
    if not experiment_id:
        raise ExperimentNotebookError("experiment_id is required for non-create experiment records")
    if entry_type == "experiment":
        if action not in {"status", "scope_update"}:
            raise ExperimentNotebookError("experiment entries after creation support status or scope_update")
        if action == "status" and not payload.get("status"):
            raise ExperimentNotebookError("experiment/status requires payload.status")
        if action == "scope_update":
            if not payload.get("scope_paths"):
                raise ExperimentNotebookError("experiment/scope_update requires payload.scope_paths")
            root = resolve_project_root(project_root=project_root)
            payload = dict(payload)
            payload["scope_paths"] = sorted({
                resolve_project_path(value, project_root=str(root)).relative_to(root).as_posix() or "."
                for value in payload["scope_paths"]
            })
    attempt_id = payload.get("attempt_id")
    if entry_type == "attempt" and action == "define" and not attempt_id:
        attempt_id = f"att_{uuid.uuid4().hex[:12]}"
    common = {"attempt_id", "status", "evidence", "next_action", "details"}
    details = dict(payload.get("details") or {})
    details.update({key: value for key, value in payload.items() if key not in common})
    appended = append_experiment_entry(
        project_root,
        experiment_id=experiment_id,
        entry_type=entry_type,
        action=action,
        summary=params["summary"],
        status=payload.get("status"),
        attempt_id=attempt_id,
        parent_entry_ids=params.get("parent_entry_ids"),
        runtime_record_ids=params.get("runtime_record_ids"),
        evidence=payload.get("evidence"),
        details=details,
        next_action=payload.get("next_action"),
        idempotency_key=params.get("idempotency_key"),
    )
    rebuild_project_summary(project_root)
    return {
        **appended,
        "path": str(appended["path"].relative_to(appended["path"].parents[2])),
    }


def execute(params: dict) -> dict:
    project_root = params.get("project_root")
    if not project_root:
        return {"status": "error", "message": "project_root is required"}
    try:
        channel = params.get("channel", "operational")
        if channel == "experiment":
            data = _experiment_record(params)
            return {"status": "success", "project_root": project_root, "data": data}
        if channel != "operational":
            raise ValueError(f"Unsupported record channel: {channel}")
        mixed = sorted(set(params) & _EXPERIMENT_ONLY_KEYS)
        if mixed:
            raise ValueError(f"Operational record cannot contain experiment-entry fields: {mixed}")
        if params.get("kind") == "migration":
            data = apply_migration(
                project_root,
                migration_report_hash=params.get("migration_report_hash", ""),
                confirm_migration=params.get("confirm_migration") is True,
                summary=params.get("summary", "Index legacy SimFlow state"),
            )
            return {"status": "success", "project_root": project_root, "data": data}
        data = record_event(
            project_root,
            kind=params.get("kind", ""),
            summary=params.get("summary", ""),
            status=params.get("status"),
            stage=params.get("stage"),
            run_id=params.get("run_id"),
            goal=params.get("goal"),
            next_action=params.get("next_action"),
            artifacts=params.get("artifacts"),
            parent_ids=params.get("parent_ids"),
            details=params.get("details"),
            experiment_id=params.get("experiment_id"),
            attempt_id=params.get("attempt_id"),
            idempotency_key=params.get("idempotency_key"),
        )
    except (ExperimentNotebookError, MigrationError, ProjectRootError, TypeError, ValueError) as error:
        return {"status": "error", "message": str(error)}
    return {"status": "success", "project_root": project_root, "data": data}
