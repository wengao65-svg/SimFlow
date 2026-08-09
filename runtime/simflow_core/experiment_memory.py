"""Forward-only experiment memory for cross-session project continuity."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .state import resolve_project_path, resolve_project_root


MEMORY_DIR = Path(".simflow/memory")
LEDGER_FILE = "ledger.json"
EXPERIMENTS_FILE = "experiments.json"
ITERATIONS_FILE = "iterations.json"
ACTIVITY_EVENTS_FILE = "activity_events.jsonl"
SESSION_CONTEXTS_FILE = "session_contexts.jsonl"
SESSION_HANDOFFS_FILE = "session_handoffs.jsonl"
LEDGER_SCHEMA_VERSION = "simflow.experiment_ledger.v1"
SESSION_TIMEOUT_SECONDS = int(os.environ.get("SIMFLOW_SESSION_TIMEOUT_MIN", "30")) * 60

EXPERIMENT_STATUSES = {"active", "paused", "completed", "failed", "abandoned"}
ITERATION_STATUSES = {"planned", "running", "evaluating", "accepted", "rejected", "failed", "paused", "superseded"}
ACTIVITY_TERMINAL_STATUSES = {"completed", "partial", "failed", "paused", "cancelled"}

_SECRET_PATTERN = re.compile(
    r"(?i)(api[_-]?key|token|password|secret|authorization)\s*[:=]\s*([^\s,;]+)"
)


class ExperimentMemoryError(ValueError):
    """Raised when experiment-memory state or context is invalid."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now_epoch() -> float:
    return time.time()


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _paths(root: Path) -> dict[str, Path]:
    base = root / MEMORY_DIR
    return {
        "base": base,
        "ledger": base / LEDGER_FILE,
        "experiments": base / EXPERIMENTS_FILE,
        "iterations": base / ITERATIONS_FILE,
        "activities": base / ACTIVITY_EVENTS_FILE,
        "contexts": base / SESSION_CONTEXTS_FILE,
        "handoffs": base / SESSION_HANDOFFS_FILE,
    }


def _read_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return default


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    records = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    value = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(value, dict):
                    records.append(value)
    except OSError:
        return []
    return records


def _write_json_atomic(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.stem}.", suffix=".tmp", dir=str(path.parent))
    temp = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.replace(str(temp), str(path))
    except Exception:
        temp.unlink(missing_ok=True)
        raise


def _append_jsonl(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _sanitize_command(command: str | None) -> tuple[str | None, str | None]:
    if not command:
        return None, None
    raw = str(command)
    redacted = _SECRET_PATTERN.sub(r"\1=[REDACTED]", raw)
    return redacted, hashlib.sha256(raw.encode("utf-8")).hexdigest()


def is_ledger_enabled(project_root: str) -> bool:
    root = resolve_project_root(project_root=project_root)
    ledger = _read_json(_paths(root)["ledger"], {})
    return isinstance(ledger, dict) and ledger.get("schema_version") == LEDGER_SCHEMA_VERSION


def _ensure_ledger(root: Path) -> dict[str, Any]:
    paths = _paths(root)
    ledger = _read_json(paths["ledger"], {})
    if ledger.get("schema_version") == LEDGER_SCHEMA_VERSION:
        return ledger
    now = _now_iso()
    ledger = {
        "schema_version": LEDGER_SCHEMA_VERSION,
        "history_mode": "forward_only",
        "history_start": now,
        "legacy_history_imported": False,
        "project_root": str(root),
        "created_at": now,
        "updated_at": now,
    }
    _write_json_atomic(paths["ledger"], ledger)
    _write_json_atomic(paths["experiments"], [])
    _write_json_atomic(paths["iterations"], [])
    for name in ("activities", "handoffs"):
        paths[name].parent.mkdir(parents=True, exist_ok=True)
        paths[name].touch(exist_ok=True)
    return ledger


def _context_events(root: Path) -> list[dict[str, Any]]:
    return _read_jsonl(_paths(root)["contexts"])


def create_session_context(project_root: str, *, working_directory: str | None = None) -> dict[str, Any]:
    root = resolve_project_root(project_root=project_root)
    if working_directory:
        resolve_project_path(working_directory, project_root=str(root))
    context_id = _id("ctx")
    event = {
        "event": "opened",
        "session_context_id": context_id,
        "project_root": str(root),
        "working_directory": working_directory or str(root),
        "ts": _now_iso(),
        "_ts_epoch": _now_epoch(),
    }
    _append_jsonl(_paths(root)["contexts"], event)
    return event


def validate_session_context(project_root: str, session_context_id: str, *, touch: bool = False) -> dict[str, Any]:
    if not session_context_id:
        raise ExperimentMemoryError("session_context_id is required; call project_reentry first")
    root = resolve_project_root(project_root=project_root)
    latest = None
    for event in _context_events(root):
        if event.get("session_context_id") == session_context_id:
            latest = event
    if not latest:
        raise ExperimentMemoryError("Unknown session_context_id; call project_reentry again")
    if latest.get("event") == "closed":
        raise ExperimentMemoryError("session_context_id is closed; call project_reentry again")
    age = _now_epoch() - float(latest.get("_ts_epoch", 0))
    if age > SESSION_TIMEOUT_SECONDS:
        raise ExperimentMemoryError("session_context_id expired; call project_reentry again")
    if touch:
        latest = {
            **latest,
            "event": "touched",
            "ts": _now_iso(),
            "_ts_epoch": _now_epoch(),
        }
        _append_jsonl(_paths(root)["contexts"], latest)
    return latest


def close_session_context(project_root: str, session_context_id: str) -> None:
    root = resolve_project_root(project_root=project_root)
    current = validate_session_context(str(root), session_context_id)
    _append_jsonl(_paths(root)["contexts"], {
        **current,
        "event": "closed",
        "ts": _now_iso(),
        "_ts_epoch": _now_epoch(),
    })


def _load_records(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    paths = _paths(root)
    experiments = _read_json(paths["experiments"], [])
    iterations = _read_json(paths["iterations"], [])
    activities = _read_jsonl(paths["activities"])
    return (
        experiments if isinstance(experiments, list) else [],
        iterations if isinstance(iterations, list) else [],
        activities,
    )


def _find(records: list[dict[str, Any]], key: str, value: str, label: str) -> dict[str, Any]:
    for record in records:
        if record.get(key) == value:
            return record
    raise ExperimentMemoryError(f"Unknown {label}: {value}")


def _replace(records: list[dict[str, Any]], key: str, value: str, updated: dict[str, Any]) -> list[dict[str, Any]]:
    return [updated if item.get(key) == value else item for item in records]


def _criteria(value: Any) -> list[dict[str, Any]]:
    if not value:
        return []
    if not isinstance(value, list):
        raise ExperimentMemoryError("acceptance_criteria must be an array")
    result = []
    for index, item in enumerate(value, start=1):
        if isinstance(item, str):
            item = {"description": item}
        if not isinstance(item, dict) or not item.get("description"):
            raise ExperimentMemoryError("Each acceptance criterion requires a description")
        result.append({"criterion_id": item.get("criterion_id") or f"criterion_{index:03d}", **item})
    return result


def begin_experiment(
    project_root: str,
    *,
    session_context_id: str,
    title: str,
    objective: str,
    stage: str,
    root_path: str,
    recipe: str | None = None,
    acceptance_criteria: Any = None,
    next_action: str | None = None,
) -> dict[str, Any]:
    root = resolve_project_root(project_root=project_root)
    validate_session_context(str(root), session_context_id, touch=True)
    _ensure_ledger(root)
    experiment_path = resolve_project_path(root_path, project_root=str(root))
    experiments, _, _ = _load_records(root)
    now = _now_iso()
    experiment = {
        "experiment_id": _id("exp"),
        "title": title,
        "objective": objective,
        "stage": stage,
        "recipe": recipe,
        "root_path": str(experiment_path.relative_to(root)) if experiment_path != root else ".",
        "status": "active",
        "acceptance_criteria": _criteria(acceptance_criteria),
        "current_iteration_id": None,
        "next_action": next_action,
        "history_scope": "from_experiment_creation_only",
        "legacy_inputs": [],
        "created_at": now,
        "updated_at": now,
        "completed_at": None,
    }
    _write_json_atomic(_paths(root)["experiments"], [*experiments, experiment])
    render_experiment_notebook(str(root), experiment["experiment_id"])
    return experiment


def finish_experiment(
    project_root: str,
    *,
    session_context_id: str,
    experiment_id: str,
    status: str,
    conclusion: str | None = None,
    next_action: str | None = None,
) -> dict[str, Any]:
    if status not in EXPERIMENT_STATUSES - {"active"}:
        raise ExperimentMemoryError(f"Unsupported terminal experiment status: {status}")
    root = resolve_project_root(project_root=project_root)
    validate_session_context(str(root), session_context_id, touch=True)
    experiments, _, _ = _load_records(root)
    current = _find(experiments, "experiment_id", experiment_id, "experiment")
    now = _now_iso()
    updated = {**current, "status": status, "conclusion": conclusion, "next_action": next_action, "updated_at": now}
    if status in {"completed", "failed", "abandoned"}:
        updated["completed_at"] = now
    _write_json_atomic(_paths(root)["experiments"], _replace(experiments, "experiment_id", experiment_id, updated))
    render_experiment_notebook(str(root), experiment_id)
    return updated


def begin_iteration(
    project_root: str,
    *,
    session_context_id: str,
    experiment_id: str,
    objective: str,
    acceptance_criteria: Any,
    parent_iteration_id: str | None = None,
    inputs: list[Any] | None = None,
    next_action: str | None = None,
) -> dict[str, Any]:
    root = resolve_project_root(project_root=project_root)
    validate_session_context(str(root), session_context_id, touch=True)
    experiments, iterations, _ = _load_records(root)
    experiment = _find(experiments, "experiment_id", experiment_id, "experiment")
    related = [item for item in iterations if item.get("experiment_id") == experiment_id]
    if parent_iteration_id:
        _find(related, "iteration_id", parent_iteration_id, "parent iteration")
    now = _now_iso()
    iteration = {
        "iteration_id": _id("iter"),
        "experiment_id": experiment_id,
        "sequence": len(related) + 1,
        "parent_iteration_id": parent_iteration_id,
        "objective": objective,
        "status": "running",
        "acceptance_criteria": _criteria(acceptance_criteria),
        "criterion_results": [],
        "inputs": inputs or [],
        "recovery": None,
        "decision": None,
        "next_action": next_action,
        "created_at": now,
        "updated_at": now,
        "completed_at": None,
    }
    _write_json_atomic(_paths(root)["iterations"], [*iterations, iteration])
    updated_experiment = {**experiment, "current_iteration_id": iteration["iteration_id"], "next_action": next_action, "updated_at": now}
    _write_json_atomic(_paths(root)["experiments"], _replace(experiments, "experiment_id", experiment_id, updated_experiment))
    render_experiment_notebook(str(root), experiment_id)
    return iteration


def evaluate_iteration(
    project_root: str,
    *,
    session_context_id: str,
    experiment_id: str,
    iteration_id: str,
    status: str,
    criterion_results: list[dict[str, Any]],
    decision: str,
    next_action: str | None = None,
    recovery: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if status not in ITERATION_STATUSES:
        raise ExperimentMemoryError(f"Unsupported iteration status: {status}")
    root = resolve_project_root(project_root=project_root)
    validate_session_context(str(root), session_context_id, touch=True)
    experiments, iterations, _ = _load_records(root)
    experiment = _find(experiments, "experiment_id", experiment_id, "experiment")
    iteration = _find(iterations, "iteration_id", iteration_id, "iteration")
    if iteration.get("experiment_id") != experiment_id:
        raise ExperimentMemoryError("iteration_id does not belong to experiment_id")
    now = _now_iso()
    updated = {
        **iteration,
        "status": status,
        "criterion_results": criterion_results or [],
        "decision": decision,
        "next_action": next_action,
        "recovery": recovery,
        "updated_at": now,
        "completed_at": now if status in {"accepted", "rejected", "failed", "superseded"} else None,
    }
    _write_json_atomic(_paths(root)["iterations"], _replace(iterations, "iteration_id", iteration_id, updated))
    updated_experiment = {**experiment, "next_action": next_action, "updated_at": now}
    _write_json_atomic(_paths(root)["experiments"], _replace(experiments, "experiment_id", experiment_id, updated_experiment))
    render_experiment_notebook(str(root), experiment_id)
    return updated


def start_activity(
    project_root: str,
    *,
    session_context_id: str,
    experiment_id: str,
    objective: str,
    activity_type: str,
    stage: str,
    iteration_id: str | None = None,
    method: str | None = None,
    software: str | None = None,
    version: str | None = None,
    scripts: list[dict[str, Any]] | None = None,
    command: str | None = None,
    inputs: list[Any] | None = None,
    parameters: dict[str, Any] | None = None,
    expected_outputs: list[Any] | None = None,
    gate_ids: list[str] | None = None,
) -> dict[str, Any]:
    root = resolve_project_root(project_root=project_root)
    validate_session_context(str(root), session_context_id, touch=True)
    experiments, iterations, _ = _load_records(root)
    _find(experiments, "experiment_id", experiment_id, "experiment")
    if iteration_id:
        iteration = _find(iterations, "iteration_id", iteration_id, "iteration")
        if iteration.get("experiment_id") != experiment_id:
            raise ExperimentMemoryError("iteration_id does not belong to experiment_id")
    command_redacted, command_sha256 = _sanitize_command(command)
    event = {
        "event_id": _id("evt"),
        "event_type": "activity_started",
        "activity_id": _id("act"),
        "session_context_id": session_context_id,
        "experiment_id": experiment_id,
        "iteration_id": iteration_id,
        "activity_type": activity_type,
        "objective": objective,
        "stage": stage,
        "status": "running",
        "method": method,
        "software": software,
        "version": version,
        "scripts": scripts or [],
        "command_redacted": command_redacted,
        "command_sha256": command_sha256,
        "inputs": inputs or [],
        "parameters": parameters or {},
        "expected_outputs": expected_outputs or [],
        "gate_ids": gate_ids or [],
        "started_at": _now_iso(),
    }
    _append_jsonl(_paths(root)["activities"], event)
    render_experiment_notebook(str(root), experiment_id)
    return event


def _activity_projection(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    projected: dict[str, dict[str, Any]] = {}
    for event in events:
        activity_id = event.get("activity_id")
        if not activity_id:
            continue
        projected[activity_id] = {**projected.get(activity_id, {}), **event}
    return projected


def validate_activity_binding(
    project_root: str,
    *,
    session_context_id: str,
    experiment_id: str,
    activity_id: str,
) -> dict[str, Any]:
    """Validate an active ledger activity before a related state write."""
    root = resolve_project_root(project_root=project_root)
    validate_session_context(str(root), session_context_id, touch=True)
    experiments, _, events = _load_records(root)
    _find(experiments, "experiment_id", experiment_id, "experiment")
    activity = _activity_projection(events).get(activity_id)
    if not activity or activity.get("experiment_id") != experiment_id:
        raise ExperimentMemoryError("activity_id does not belong to experiment_id")
    if activity.get("status") != "running":
        raise ExperimentMemoryError("activity_id is not active")
    return activity


def finish_activity(
    project_root: str,
    *,
    session_context_id: str,
    experiment_id: str,
    activity_id: str,
    status: str,
    outputs: list[Any] | None = None,
    artifact_ids: list[str] | None = None,
    job_ids: list[str] | None = None,
    checkpoint_id: str | None = None,
    observations: str | None = None,
    metrics: dict[str, Any] | None = None,
    failure: dict[str, Any] | None = None,
    restart_from: dict[str, Any] | None = None,
    next_action: str | None = None,
) -> dict[str, Any]:
    if status not in ACTIVITY_TERMINAL_STATUSES:
        raise ExperimentMemoryError(f"Unsupported activity terminal status: {status}")
    root = resolve_project_root(project_root=project_root)
    validate_session_context(str(root), session_context_id, touch=True)
    experiments, iterations, events = _load_records(root)
    experiment = _find(experiments, "experiment_id", experiment_id, "experiment")
    activity = _activity_projection(events).get(activity_id)
    if not activity or activity.get("experiment_id") != experiment_id:
        raise ExperimentMemoryError("activity_id does not belong to experiment_id")
    if activity.get("status") in ACTIVITY_TERMINAL_STATUSES:
        raise ExperimentMemoryError("activity_id is already finished")
    event = {
        "event_id": _id("evt"),
        "event_type": "activity_finished",
        "activity_id": activity_id,
        "session_context_id": session_context_id,
        "experiment_id": experiment_id,
        "iteration_id": activity.get("iteration_id"),
        "status": status,
        "outputs": outputs or [],
        "artifact_ids": artifact_ids or [],
        "job_ids": job_ids or [],
        "checkpoint_id": checkpoint_id,
        "observations": observations,
        "metrics": metrics or {},
        "failure": failure,
        "restart_from": restart_from,
        "next_action": next_action,
        "finished_at": _now_iso(),
    }
    _append_jsonl(_paths(root)["activities"], event)
    now = event["finished_at"]
    updated_experiment = {**experiment, "next_action": next_action, "updated_at": now}
    _write_json_atomic(_paths(root)["experiments"], _replace(experiments, "experiment_id", experiment_id, updated_experiment))
    iteration_id = activity.get("iteration_id")
    if iteration_id and restart_from:
        iteration = _find(iterations, "iteration_id", iteration_id, "iteration")
        updated_iteration = {**iteration, "recovery": restart_from, "next_action": next_action, "updated_at": now}
        _write_json_atomic(_paths(root)["iterations"], _replace(iterations, "iteration_id", iteration_id, updated_iteration))
    render_experiment_notebook(str(root), experiment_id)
    return event


def _select_experiment(
    root: Path,
    experiments: list[dict[str, Any]],
    *,
    experiment_id: str | None,
    working_directory: str | None,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], str | None]:
    active = [item for item in experiments if item.get("status") in {"active", "paused"}]
    if experiment_id:
        return _find(experiments, "experiment_id", experiment_id, "experiment"), active, None
    if working_directory:
        current = resolve_project_path(working_directory, project_root=str(root))
        matches = []
        for item in active:
            path = resolve_project_path(item.get("root_path") or ".", project_root=str(root))
            try:
                current.relative_to(path)
            except ValueError:
                continue
            matches.append((len(path.parts), item))
        if matches:
            matches.sort(key=lambda value: value[0], reverse=True)
            return matches[0][1], active, None
    if len(active) == 1:
        return active[0], active, None
    if len(active) > 1:
        return None, active, "multiple_active_experiments"
    return None, active, None


def build_reentry_summary(
    project_root: str,
    *,
    experiment_id: str | None = None,
    working_directory: str | None = None,
    recent_limit: int = 10,
) -> dict[str, Any]:
    root = resolve_project_root(project_root=project_root)
    paths = _paths(root)
    ledger = _read_json(paths["ledger"], {})
    enabled = ledger.get("schema_version") == LEDGER_SCHEMA_VERSION
    experiments, iterations, events = _load_records(root) if enabled else ([], [], [])
    selected, active, selection_reason = _select_experiment(
        root, experiments, experiment_id=experiment_id, working_directory=working_directory
    )
    projection = _activity_projection(events)
    selected_events = []
    selected_iterations = []
    interrupted = []
    latest_failure = None
    latest_completed = None
    if selected:
        selected_events = [event for event in events if event.get("experiment_id") == selected["experiment_id"]]
        selected_iterations = [item for item in iterations if item.get("experiment_id") == selected["experiment_id"]]
        interrupted = [item for item in projection.values() if item.get("experiment_id") == selected["experiment_id"] and item.get("status") == "running"]
        terminal = [item for item in projection.values() if item.get("experiment_id") == selected["experiment_id"]]
        terminal.sort(key=lambda item: item.get("finished_at") or item.get("started_at") or "")
        failures = [item for item in terminal if item.get("status") == "failed"]
        completed = [item for item in terminal if item.get("status") in {"completed", "partial"}]
        latest_failure = failures[-1] if failures else None
        latest_completed = completed[-1] if completed else None
    current_iteration = None
    if selected and selected.get("current_iteration_id"):
        current_iteration = next((item for item in selected_iterations if item.get("iteration_id") == selected["current_iteration_id"]), None)
    latest_event_checkpoint = None
    latest_successful_checkpoint = None
    if selected:
        from .checkpoints import get_latest_checkpoint, get_latest_recovery_checkpoint

        event_checkpoint = get_latest_checkpoint(
            project_root=str(root),
            experiment_id=selected["experiment_id"],
        )
        checkpoint = None
        if current_iteration:
            checkpoint = get_latest_recovery_checkpoint(
                project_root=str(root),
                experiment_id=selected["experiment_id"],
                iteration_id=current_iteration["iteration_id"],
            )
        if checkpoint is None:
            checkpoint = get_latest_recovery_checkpoint(
                project_root=str(root),
                experiment_id=selected["experiment_id"],
            )
        def compact_checkpoint(value: dict[str, Any] | None) -> dict[str, Any] | None:
            if not value:
                return None
            return {
                key: value.get(key)
                for key in (
                    "checkpoint_id", "stage_id", "job_id", "experiment_id",
                    "iteration_id", "activity_id", "description", "status",
                    "recoverable", "created_at",
                )
            }

        latest_event_checkpoint = compact_checkpoint(event_checkpoint)
        latest_successful_checkpoint = compact_checkpoint(checkpoint)
    explicit_recovery = (current_iteration or {}).get("recovery")
    return {
        "status": "success",
        "project_root": str(root),
        "ledger": ledger if enabled else {
            "status": "not_started",
            "history_mode": "forward_only",
            "legacy_history_imported": False,
            "legacy_history_not_imported": True,
        },
        "selection_required": selection_reason is not None,
        "selection_reason": selection_reason,
        "active_experiments": [
            {key: item.get(key) for key in ("experiment_id", "title", "root_path", "status", "current_iteration_id", "next_action")}
            for item in active
        ],
        "selected_experiment": selected,
        "current_iteration": current_iteration,
        "interrupted_activities": interrupted,
        "latest_completed_activity": latest_completed,
        "latest_failure": latest_failure,
        "latest_event_checkpoint": latest_event_checkpoint,
        "latest_successful_checkpoint": latest_successful_checkpoint,
        "latest_recovery": explicit_recovery or latest_successful_checkpoint,
        "recent_events": selected_events[-max(1, min(int(recent_limit), 50)):],
        "next_action": (current_iteration or {}).get("next_action") or (selected or {}).get("next_action"),
        "legacy_state_policy": "Legacy .simflow/state remains queryable but never determines experiment selection, recovery, or next_action.",
    }


def project_reentry(
    project_root: str,
    *,
    experiment_id: str | None = None,
    working_directory: str | None = None,
    recent_limit: int = 10,
) -> dict[str, Any]:
    root = resolve_project_root(project_root=project_root)
    context = create_session_context(str(root), working_directory=working_directory)
    summary = build_reentry_summary(
        str(root), experiment_id=experiment_id, working_directory=working_directory, recent_limit=recent_limit
    )
    summary["session_context_id"] = context["session_context_id"]
    return summary


def experiment_timeline(
    project_root: str,
    *,
    experiment_id: str,
    iteration_id: str | None = None,
    status: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> dict[str, Any]:
    root = resolve_project_root(project_root=project_root)
    experiments, iterations, events = _load_records(root)
    experiment = _find(experiments, "experiment_id", experiment_id, "experiment")
    projection = list(_activity_projection(events).values())
    records = [item for item in projection if item.get("experiment_id") == experiment_id]
    if iteration_id:
        records = [item for item in records if item.get("iteration_id") == iteration_id]
    if status:
        records = [item for item in records if item.get("status") == status]
    page = records[max(offset, 0):max(offset, 0) + max(1, min(limit, 200))]
    return {
        "status": "success",
        "project_root": str(root),
        "experiment": experiment,
        "iterations": [item for item in iterations if item.get("experiment_id") == experiment_id],
        "activities": page,
        "total": len(records),
        "offset": max(offset, 0),
        "limit": max(1, min(limit, 200)),
    }


def session_handoff(
    project_root: str,
    *,
    session_context_id: str,
    experiment_id: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    root = resolve_project_root(project_root=project_root)
    validate_session_context(str(root), session_context_id)
    summary = build_reentry_summary(str(root), experiment_id=experiment_id)
    handoff = {
        "handoff_id": _id("handoff"),
        "session_context_id": session_context_id,
        "experiment_id": (summary.get("selected_experiment") or {}).get("experiment_id"),
        "current_iteration_id": (summary.get("current_iteration") or {}).get("iteration_id"),
        "interrupted_activity_ids": [item.get("activity_id") for item in summary.get("interrupted_activities", [])],
        "latest_completed_activity_id": (summary.get("latest_completed_activity") or {}).get("activity_id"),
        "latest_failure_activity_id": (summary.get("latest_failure") or {}).get("activity_id"),
        "latest_event_checkpoint_id": (summary.get("latest_event_checkpoint") or {}).get("checkpoint_id"),
        "latest_recovery_checkpoint_id": (summary.get("latest_successful_checkpoint") or {}).get("checkpoint_id"),
        "latest_recovery": summary.get("latest_recovery"),
        "next_action": summary.get("next_action"),
        "note": note,
        "created_at": _now_iso(),
    }
    _append_jsonl(_paths(root)["handoffs"], handoff)
    close_session_context(str(root), session_context_id)
    return handoff


def render_experiment_notebook(project_root: str, experiment_id: str) -> Path:
    root = resolve_project_root(project_root=project_root)
    experiments, iterations, events = _load_records(root)
    experiment = _find(experiments, "experiment_id", experiment_id, "experiment")
    projected = [item for item in _activity_projection(events).values() if item.get("experiment_id") == experiment_id]
    related_iterations = [item for item in iterations if item.get("experiment_id") == experiment_id]
    lines = [
        f"# {experiment.get('title', experiment_id)}",
        "",
        f"- Experiment ID: {experiment_id}",
        f"- Status: {experiment.get('status')}",
        f"- Stage: {experiment.get('stage')}",
        f"- Recipe: {experiment.get('recipe') or 'unspecified'}",
        f"- Root path: {experiment.get('root_path')}",
        f"- Objective: {experiment.get('objective')}",
        f"- Next action: {experiment.get('next_action') or 'unspecified'}",
        "- History scope: forward-only from experiment creation",
        "",
        "## Iterations",
        "",
    ]
    if not related_iterations:
        lines.append("(no iterations)")
    for item in related_iterations:
        lines.append(
            f"- {item.get('iteration_id')} | {item.get('status')} | {item.get('objective')} | next: {item.get('next_action') or 'unspecified'}"
        )
    lines.extend(["", "## Activities", ""])
    if not projected:
        lines.append("(no activities)")
    for item in projected:
        lines.append(
            f"- {item.get('activity_id')} | {item.get('status')} | {item.get('activity_type')} | {item.get('objective')}"
        )
        if item.get("software") or item.get("method"):
            lines.append(f"  Software/method: {item.get('software') or 'unspecified'} / {item.get('method') or 'unspecified'}")
        if item.get("next_action"):
            lines.append(f"  Next: {item.get('next_action')}")
    report = root / ".simflow" / "reports" / "experiments" / f"{experiment_id}.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report
