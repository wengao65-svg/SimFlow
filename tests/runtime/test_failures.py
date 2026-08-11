"""Tests for centralized failure evidence and recovery recording."""

import json
from pathlib import Path

from runtime.simflow_core.checkpoints import create_checkpoint, get_latest_recovery_checkpoint
from runtime.simflow_core.failures import record_stage_failure
from runtime.simflow_core.state import init_workflow, read_state, update_stage


def test_record_stage_failure_creates_evidence_checkpoint_and_recovery_target(tmp_path):
    workflow = init_workflow("custom", "computation", project_root=str(tmp_path))
    update_stage("computation", "in_progress", project_root=str(tmp_path))
    success = create_checkpoint(
        workflow["workflow_id"],
        "computation",
        "Known-good dry-run state",
        project_root=str(tmp_path),
    )

    result = record_stage_failure(
        project_root=str(tmp_path),
        stage_name="computation",
        activity="compute",
        message="solver failed token=do-not-store",
        reason_code="solver_error",
        exception_type="RuntimeError",
        traceback_text="RuntimeError: password=hunter2",
    )

    workflow_state = read_state(project_root=str(tmp_path), state_file="workflow.json")
    summary = read_state(project_root=str(tmp_path), state_file="summary.json")
    stages = read_state(project_root=str(tmp_path), state_file="stages.json")
    checkpoints = read_state(project_root=str(tmp_path), state_file="checkpoints.json")
    verifications = read_state(project_root=str(tmp_path), state_file="verification.json")
    artifacts = read_state(project_root=str(tmp_path), state_file="artifacts.json")
    failure_checkpoint = json.loads(
        (tmp_path / ".simflow" / "checkpoints" / f"{result['failure_checkpoint_id']}.json").read_text()
    )

    assert workflow_state["status"] == summary["status"] == "failed"
    assert stages["computation"]["status"] == "failed"
    assert stages["computation"]["checkpoint_id"] == success["checkpoint_id"]
    assert stages["computation"]["failure_checkpoint_id"] == result["failure_checkpoint_id"]
    assert result["recovery_checkpoint_id"] == success["checkpoint_id"]
    assert get_latest_recovery_checkpoint(project_root=str(tmp_path))["checkpoint_id"] == success["checkpoint_id"]
    assert checkpoints[-1]["status"] == "failure"
    assert failure_checkpoint["recoverable"] is False
    assert failure_checkpoint["failure_context"]["recovery_checkpoint_id"] == success["checkpoint_id"]
    assert verifications[-1]["status"] == "fail"
    assert {artifact["type"] for artifact in artifacts[-2:]} == {"failure_log", "error_report"}

    log_text = (tmp_path / ".simflow" / "logs" / "errors" / f"{result['failure_id']}.log").read_text()
    report_text = (tmp_path / result["error_report"]).read_text()
    assert "do-not-store" not in log_text + report_text
    assert "hunter2" not in log_text + report_text
    assert "[REDACTED]" in log_text + report_text


def test_retry_clears_stale_failure_fields(tmp_path):
    init_workflow("custom", "computation", project_root=str(tmp_path))
    record_stage_failure(
        project_root=str(tmp_path),
        stage_name="computation",
        message="first attempt failed",
    )

    stage = update_stage("computation", "in_progress", project_root=str(tmp_path))
    assert stage["error_message"] is None
    assert stage["error_report_artifact_id"] is None
    assert stage["failure_id"] is None


def test_failure_recovery_uses_latest_matching_checkpoint_without_ledger_context(tmp_path):
    workflow = init_workflow("custom", "computation", project_root=str(tmp_path))
    update_stage("computation", "in_progress", project_root=str(tmp_path))
    create_checkpoint(
        workflow["workflow_id"],
        "computation",
        "other experiment recovery",
        project_root=str(tmp_path),
        experiment_id="exp_other000",
    )
    own_checkpoint = create_checkpoint(
        workflow["workflow_id"],
        "computation",
        "current experiment recovery",
        project_root=str(tmp_path),
        experiment_id="exp_current0",
        iteration_id="iter_current",
        activity_id="act_prepare0",
    )

    result = record_stage_failure(
        project_root=str(tmp_path),
        stage_name="computation",
        message="current experiment failed",
        experiment_id="exp_current0",
        iteration_id="iter_current",
        activity_id="act_failed00",
    )
    artifacts = read_state(project_root=str(tmp_path), state_file="artifacts.json")

    assert result["recovery_checkpoint_id"] == own_checkpoint["checkpoint_id"]
    assert {artifact["type"] for artifact in artifacts[-2:]} == {"failure_log", "error_report"}
    assert all("experiment_id" not in artifact for artifact in artifacts[-2:])
