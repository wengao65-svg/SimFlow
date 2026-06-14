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
) -> dict[str, Any]:
    """Write and register a real-submit job record artifact."""
    root = Path(project_root).expanduser().resolve()
    workflow = read_state(project_root=str(root), state_file="workflow.json")
    if not workflow:
        return {
            "status": "error",
            "message": "No workflow state found for job record",
            "code": "missing_workflow_state",
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
