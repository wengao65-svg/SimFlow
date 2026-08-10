"""Centralized failure evidence, checkpoint, and recovery recording."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .artifacts import register_artifact
from .checkpoints import create_checkpoint, get_latest_recovery_checkpoint
from .state import (
    ensure_workflow_initialized,
    resolve_project_root,
    touch_workflow,
    update_stage,
)
from .verification import record_stage_failure_verification


_SECRET_PATTERN = re.compile(
    r"(?i)(api[_-]?key|token|password|secret|authorization)\s*[:=]\s*([^\s,;]+)"
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize(text: Optional[str]) -> str:
    return _SECRET_PATTERN.sub(r"\1=[REDACTED]", str(text or ""))


def record_stage_failure(
    *,
    project_root: str,
    stage_name: str,
    message: str,
    activity: Optional[str] = None,
    reason_code: Optional[str] = None,
    exception_type: Optional[str] = None,
    traceback_text: Optional[str] = None,
    job_id: Optional[str] = None,
    partial_artifact_ids: Optional[list[str]] = None,
    failure_id: Optional[str] = None,
    session_context_id: Optional[str] = None,
    experiment_id: Optional[str] = None,
    iteration_id: Optional[str] = None,
    activity_id: Optional[str] = None,
) -> dict[str, Any]:
    """Persist a complete, recoverable stage-failure evidence bundle."""
    root = resolve_project_root(project_root=project_root)
    from .experiment_memory import require_write_context
    ledger_context = require_write_context(
        str(root), session_context_id=session_context_id, experiment_id=experiment_id,
        iteration_id=iteration_id, activity_id=activity_id,
    )
    if ledger_context:
        session_context_id = ledger_context.session_context_id
        experiment_id = ledger_context.experiment_id
        iteration_id = ledger_context.iteration_id
        activity_id = ledger_context.activity_id
    context = {"session_context_id": session_context_id, "experiment_id": experiment_id,
               "iteration_id": iteration_id, "activity_id": activity_id}
    workflow = ensure_workflow_initialized(project_root=str(root))
    now = _now_iso()
    failure_id = failure_id or f"fail_{uuid.uuid4().hex[:8]}"
    safe_message = _sanitize(message) or "Stage execution failed"
    safe_traceback = _sanitize(traceback_text)
    partial_ids = sorted(set(partial_artifact_ids or []))

    log_rel = Path(".simflow") / "logs" / "errors" / f"{failure_id}.log"
    log_path = root / log_rel
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_lines = [
        f"failure_id: {failure_id}",
        f"workflow_id: {workflow.get('workflow_id', 'unknown')}",
        f"stage: {stage_name}",
        f"activity: {activity or 'unknown'}",
        f"reason_code: {reason_code or 'stage_execution_error'}",
        f"exception_type: {exception_type or 'unknown'}",
        f"created_at: {now}",
        "",
        safe_message,
    ]
    if safe_traceback:
        log_lines.extend(["", safe_traceback])
    log_path.write_text("\n".join(log_lines) + "\n", encoding="utf-8")

    log_artifact = register_artifact(
        name=f"{failure_id}.log",
        artifact_type="failure_log",
        stage=stage_name,
        path=str(log_rel),
        parent_artifacts=partial_ids,
        metadata={"failure_id": failure_id, "reason_code": reason_code},
        project_root=str(root),
        session_context_id=session_context_id,
        experiment_id=experiment_id,
        iteration_id=iteration_id,
        activity_id=activity_id,
    )

    report_rel = Path(".simflow") / "reports" / "errors" / f"{failure_id}.json"
    report_path = root / report_rel
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "failure_id": failure_id,
        "workflow_id": workflow.get("workflow_id", "unknown"),
        "stage": stage_name,
        "activity": activity,
        "reason_code": reason_code or "stage_execution_error",
        "exception_type": exception_type,
        "message": safe_message,
        "job_id": job_id,
        "partial_artifact_ids": partial_ids,
        "log_path": str(log_rel),
        "created_at": now,
        "experiment_id": experiment_id,
        "iteration_id": iteration_id,
        "activity_id": activity_id,
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report_artifact = register_artifact(
        name=f"{failure_id}.json",
        artifact_type="error_report",
        stage=stage_name,
        path=str(report_rel),
        parent_artifacts=[*partial_ids, log_artifact["artifact_id"]],
        metadata={"failure_id": failure_id, "reason_code": report["reason_code"]},
        project_root=str(root),
        session_context_id=session_context_id,
        experiment_id=experiment_id,
        iteration_id=iteration_id,
        activity_id=activity_id,
    )

    recovery = None
    if experiment_id:
        if iteration_id:
            recovery = get_latest_recovery_checkpoint(
                project_root=str(root),
                experiment_id=experiment_id,
                iteration_id=iteration_id,
            )
        if recovery is None:
            recovery = get_latest_recovery_checkpoint(
                project_root=str(root),
                experiment_id=experiment_id,
            )
    else:
        recovery = get_latest_recovery_checkpoint(project_root=str(root))
    recovery_checkpoint_id = recovery.get("checkpoint_id") if recovery else None
    update_stage(
        stage_name,
        "failed",
        project_root=str(root),
        error_message=safe_message,
        error_report_artifact_id=report_artifact["artifact_id"],
        failure_id=failure_id,
        **context,
    )
    touch_workflow(str(root), current_stage=stage_name, status="failed", **context)

    failure_context = {
        "failure_id": failure_id,
        "failed_activity": activity,
        "reason_code": report["reason_code"],
        "exception_type": exception_type,
        "message": safe_message,
        "error_report_artifact_id": report_artifact["artifact_id"],
        "log_artifact_ids": [log_artifact["artifact_id"]],
        "partial_artifact_ids": partial_ids,
        "recovery_checkpoint_id": recovery_checkpoint_id,
    }
    checkpoint = create_checkpoint(
        workflow_id=workflow.get("workflow_id", "unknown"),
        stage_id=stage_name,
        description=f"Failure captured for {activity or stage_name}: {safe_message}",
        status="failure",
        job_id=job_id,
        failure_context=failure_context,
        project_root=str(root),
        session_context_id=session_context_id,
        experiment_id=experiment_id,
        iteration_id=iteration_id,
        activity_id=activity_id,
    )
    verification = record_stage_failure_verification(
        stage_name,
        str(root),
        message=safe_message,
        failure_id=failure_id,
        checkpoint_id=checkpoint["checkpoint_id"],
        source_artifact_ids=[report_artifact["artifact_id"], log_artifact["artifact_id"]],
        **context,
    )

    return {
        "status": "error",
        "failure_id": failure_id,
        "reason_code": report["reason_code"],
        "message": safe_message,
        "error_report": str(report_rel),
        "error_report_artifact_id": report_artifact["artifact_id"],
        "log_artifact_id": log_artifact["artifact_id"],
        "failure_checkpoint_id": checkpoint["checkpoint_id"],
        "recovery_checkpoint_id": recovery_checkpoint_id,
        "verification_id": verification["verification_id"],
        "suggested_action": (
            f"Inspect the error report, then restore {recovery_checkpoint_id} before retrying."
            if recovery_checkpoint_id
            else "Inspect the error report, correct the failure, and retry the stage."
        ),
    }
