"""Record one compact execution event for each real submit attempt."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from runtime.simflow_core.gates import get_gate_decisions
from runtime.simflow_core.records import record_event
from runtime.simflow_core.state import resolve_project_root


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_submit_job(
    *,
    project_root: str,
    scheduler: str,
    job_id: str,
    run_plan_hash: str | None = None,
    status: str = "submitted",
    script_path: str | None = None,
    gate_decision_id: str | None = None,
    submit_result: dict[str, Any] | None = None,
    experiment_id: str | None = None,
    attempt_id: str | None = None,
) -> dict[str, Any]:
    """Append one run record after an approval-bound submit attempt."""
    root = resolve_project_root(project_root=project_root)
    if not gate_decision_id:
        return {
            "status": "error",
            "message": "record_submit_job requires an approved hpc_submit gate decision",
            "code": "gate_decision_id_required",
        }
    if not run_plan_hash:
        return {
            "status": "error",
            "message": "record_submit_job requires run_plan_hash",
            "code": "run_plan_hash_required",
        }
    matching = None
    for decision in get_gate_decisions("hpc_submit", project_root=str(root)):
        if decision.get("decision_id") == gate_decision_id:
            matching = decision
            break
    conditions = matching.get("conditions", {}) if isinstance(matching, dict) else {}
    if (
        not matching
        or matching.get("decision") != "approved"
        or conditions.get("run_plan_hash") != run_plan_hash
    ):
        return {
            "status": "error",
            "message": "gate decision is not approved for this run_plan_hash",
            "code": "run_plan_not_approved",
        }

    now = _now_iso()
    run_id = attempt_id or f"{scheduler}_{job_id}"
    record = record_event(
        str(root),
        kind="run",
        summary=f"{scheduler} submit {status}",
        status=status,
        stage="computation",
        run_id=run_id,
        experiment_id=experiment_id,
        attempt_id=attempt_id,
        details={
            "operation": "submit",
            "scheduler": scheduler,
            "job_id": str(job_id),
            "run_plan_hash": run_plan_hash,
            "script_path": script_path,
            "gate_decision_id": gate_decision_id,
            "experiment_id": experiment_id,
            "attempt_id": attempt_id,
            "submitted_at": now if status in {"submitted", "running", "completed"} else None,
            "completed_at": now if status in {"completed", "failed", "cancelled"} else None,
            "submit_result": submit_result or {},
            "execution_truth": {
                "real_submit": True,
                "approval_required_for_real_submit": True,
            },
        },
    )
    return {
        "status": "success",
        "record": record,
        "job_record": record["details"],
    }
