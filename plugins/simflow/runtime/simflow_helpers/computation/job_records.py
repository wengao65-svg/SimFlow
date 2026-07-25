"""Record real submit job evidence for computation workflows."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runtime.simflow_core.artifacts import register_artifact
from runtime.simflow_core.state import read_state, write_state


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _relative_path(project_root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(project_root.resolve()))
    except ValueError:
        return str(path.resolve())


def _job_record_id(scheduler: str, job_id: str) -> str:
    normalized = "".join(ch if ch.isalnum() else "_" for ch in f"{scheduler}_{job_id}".lower()).strip("_")
    return normalized or f"job_{uuid.uuid4().hex[:12]}"


def record_submit_job(
    *,
    project_root: str,
    scheduler: str,
    job_id: str,
    status: str = "submitted",
    script_path: str | None = None,
    gate_decision_id: str | None = None,
    dry_run_evidence: str | None = None,
    script_hash: str | None = None,
    input_artifact_hash: str | None = None,
    submit_result: dict[str, Any] | None = None,
    user_override: bool = False,
    override_gate_id: str | None = None,
) -> dict[str, Any]:
    """Write and register a real-submit job record.

    P2.4: Enforces that real job submissions have a gate_decision_id from
    an approved hpc_submit gate. Jobs without gate approval are rejected
    unless user_override=True with a corresponding override_gate_id.
    """
    root = Path(project_root).expanduser().resolve()
    workflow = read_state(project_root=str(root), state_file="workflow.json")
    if not workflow:
        return {
            "status": "error",
            "message": "No workflow state found for job record",
            "code": "missing_workflow_state",
        }

    # P2.4: Enforce gate_decision_id for real submit jobs
    if not gate_decision_id and not user_override:
        return {
            "status": "error",
            "message": (
                "record_submit_job requires a gate_decision_id from an approved "
                "hpc_submit gate. If this is a user-approved override, pass "
                "user_override=True and override_gate_id."
            ),
            "code": "gate_decision_id_required",
        }

    # If gate_decision_id is provided, verify it exists in gates.json
    if gate_decision_id:
        gates = read_state(project_root=str(root), state_file="gates.json")
        if isinstance(gates, list):
            gate_found = any(
                isinstance(g, dict) and (
                    g.get("gate_id") == gate_decision_id or
                    g.get("decision_id") == gate_decision_id
                )
                for g in gates
            )
            if not gate_found:
                return {
                    "status": "error",
                    "message": (
                        f"gate_decision_id '{gate_decision_id}' not found in "
                        f"gates.json. Record the gate approval first via "
                        f"simflow-safety-gates skill, or use user_override=True."
                    ),
                    "code": "gate_decision_not_found",
                }

    # If user_override, verify override_gate_id exists in gates.json
    if user_override and override_gate_id:
        gates = read_state(project_root=str(root), state_file="gates.json")
        if isinstance(gates, list):
            override_found = any(
                isinstance(g, dict) and g.get("gate_id") == override_gate_id
                and g.get("decision") == "user_override"
                for g in gates
            )
            if not override_found:
                return {
                    "status": "error",
                    "message": (
                        f"override_gate_id '{override_gate_id}' not found in "
                        f"gates.json with decision='user_override'. Record the "
                        f"override first via record_user_override tool."
                    ),
                    "code": "override_gate_not_found",
                }

    now = _now_iso()
    job_record = {
        "job_id": str(job_id),
        "workflow_id": workflow.get("workflow_id", "unknown"),
        "stage": "computation",
        "status": status,
        "dry_run": False,
        "scheduler": scheduler,
        "script_path": script_path,
        "gate_decision_id": gate_decision_id,
        "dry_run_evidence": dry_run_evidence,
        "script_hash": script_hash,
        "input_artifact_hash": input_artifact_hash,
        "submitted_at": now if status in {"submitted", "running", "completed"} else None,
        "completed_at": now if status in {"completed", "failed", "cancelled"} else None,
        "created_at": now,
        "submit_result": submit_result or {},
        "execution_truth": {
            "real_submit": True,
            "approval_required_for_real_submit": True,
        },
    }

    reports_dir = root / ".simflow" / "reports" / "compute" / "jobs"
    reports_dir.mkdir(parents=True, exist_ok=True)
    record_path = reports_dir / f"{_job_record_id(scheduler, str(job_id))}.json"
    record_path.write_text(json.dumps(job_record, indent=2, ensure_ascii=False), encoding="utf-8")

    artifact = register_artifact(
        record_path.name,
        "job_record_if_submitted",
        "computation",
        project_root=str(root),
        path=_relative_path(root, record_path),
        parent_artifacts=[],
        parameters={
            "scheduler": scheduler,
            "job_id": str(job_id),
            "gate_decision_id": gate_decision_id,
        },
        software=None,
        metadata={
            "evidence_keys": ["job_record_if_submitted"],
            "real_submit": True,
            "execution_truth": job_record["execution_truth"],
        },
    )

    jobs = read_state(project_root=str(root), state_file="jobs.json")
    if not isinstance(jobs, list):
        jobs = []
    jobs.append({
        **job_record,
        "path": _relative_path(root, record_path),
        "artifact_id": artifact["artifact_id"],
    })
    write_state(jobs, project_root=str(root), state_file="jobs.json")

    return {
        "status": "success",
        "job_record": job_record,
        "artifact": artifact,
        "path": _relative_path(root, record_path),
    }
