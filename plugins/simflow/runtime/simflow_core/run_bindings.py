"""Operational Experiment/Attempt bindings for immutable HPC run plans."""

from __future__ import annotations

import uuid
from typing import Any

from .experiment_notebook import experiment_notebook_path
from .records import list_project_records, record_event
from .state import resolve_project_root


def _attempt_id() -> str:
    return f"att_{uuid.uuid4().hex[:12]}"


def get_run_plan_binding(project_root: str, run_plan_hash: str) -> dict[str, Any] | None:
    """Return the latest operational binding for one immutable run plan."""
    root = resolve_project_root(project_root=project_root)
    binding = None
    for record in list_project_records(str(root), kind="run"):
        details = record.get("details") if isinstance(record.get("details"), dict) else {}
        if details.get("run_plan_hash") != run_plan_hash:
            continue
        if details.get("operation") not in {"plan", "binding_correction"}:
            continue
        binding = {
            "run_plan_hash": run_plan_hash,
            "experiment_id": record.get("experiment_id") or details.get("experiment_id"),
            "attempt_id": record.get("attempt_id") or details.get("attempt_id"),
            "binding_record_id": record.get("record_id"),
            "operation": details.get("operation"),
        }
    return binding


def bind_run_plan(
    project_root: str,
    *,
    run_plan_hash: str,
    plan_path: str,
    scheduler: str,
    script_path: str,
    submit_ready: bool,
    experiment_id: str | None = None,
    attempt_id: str | None = None,
) -> dict[str, Any]:
    """Record a plan once and append a correction when only its research binding changes."""
    root = resolve_project_root(project_root=project_root)
    if attempt_id and not experiment_id:
        raise ValueError("attempt_id requires experiment_id")
    if experiment_id and not experiment_notebook_path(str(root), experiment_id).is_file():
        raise ValueError(f"Unknown experiment_id for run plan binding: {experiment_id}")

    current = get_run_plan_binding(str(root), run_plan_hash)
    if experiment_id and not attempt_id:
        if current and current.get("experiment_id") == experiment_id and current.get("attempt_id"):
            attempt_id = current["attempt_id"]
        else:
            attempt_id = _attempt_id()

    desired = {"experiment_id": experiment_id, "attempt_id": attempt_id}
    if current is None:
        record = record_event(
            str(root),
            kind="run",
            summary="Immutable HPC run plan prepared" if submit_ready else "HPC run plan validation failed",
            status="prepared" if submit_ready else "failed",
            stage="computation",
            run_id=attempt_id or f"plan_{run_plan_hash[:12]}",
            experiment_id=experiment_id,
            attempt_id=attempt_id,
            idempotency_key=f"hpc-plan:{run_plan_hash}",
            artifacts=[{"path": plan_path, "role": "immutable_run_plan"}],
            details={
                "operation": "plan",
                "run_plan_hash": run_plan_hash,
                "scheduler": scheduler,
                "script_path": script_path,
                "submit_ready": submit_ready,
                **desired,
            },
        )
        return {**desired, "binding_record_id": record["record_id"], "operation": "plan"}

    if experiment_id is None and attempt_id is None:
        return current
    current_identity = {
        "experiment_id": current.get("experiment_id"),
        "attempt_id": current.get("attempt_id"),
    }
    if current_identity == desired:
        return current

    correction = record_event(
        str(root),
        kind="run",
        summary="Correct immutable run-plan research binding",
        status="prepared" if submit_ready else "failed",
        stage="computation",
        run_id=attempt_id or f"plan_{run_plan_hash[:12]}",
        experiment_id=experiment_id,
        attempt_id=attempt_id,
        idempotency_key=f"hpc-binding:{run_plan_hash}:{experiment_id}:{attempt_id}",
        parent_ids=[current["binding_record_id"]],
        details={
            "operation": "binding_correction",
            "run_plan_hash": run_plan_hash,
            "previous_binding": current_identity,
            **desired,
        },
    )
    return {**desired, "binding_record_id": correction["record_id"], "operation": "binding_correction"}


def find_job_run_plan_hash(project_root: str, job_id: str) -> str | None:
    """Find the latest recorded immutable plan for a submitted scheduler job."""
    root = resolve_project_root(project_root=project_root)
    for record in reversed(list_project_records(str(root), kind="run")):
        details = record.get("details") if isinstance(record.get("details"), dict) else {}
        if str(details.get("job_id", "")) == str(job_id) and details.get("run_plan_hash"):
            return str(details["run_plan_hash"])
    return None


def latest_job_status(project_root: str, job_id: str) -> str | None:
    """Return the latest recorded status for one scheduler job."""
    root = resolve_project_root(project_root=project_root)
    for record in reversed(list_project_records(str(root), kind="run")):
        details = record.get("details") if isinstance(record.get("details"), dict) else {}
        if str(details.get("job_id", "")) == str(job_id):
            return record.get("status")
    return None

