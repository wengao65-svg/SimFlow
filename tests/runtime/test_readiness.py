#!/usr/bin/env python3
"""Tests for read-only stage readiness diagnostics."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "runtime"))

from runtime.simflow_core.artifacts import register_artifact
from runtime.simflow_core.checkpoints import create_checkpoint
from runtime.simflow_core.gates import record_gate_decision
from runtime.simflow_core.readiness import build_project_readiness, build_stage_readiness
from runtime.simflow_core.state import init_workflow, update_stage


def _write(root: Path, relative_path: str, content: str = "content\n") -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _register_evidence(root: Path, stage: str, evidence_key: str) -> dict:
    path = f"{stage}/{evidence_key}.json"
    _write(root, path, "{}\n")
    return register_artifact(
        f"{evidence_key}.json",
        "custom_evidence",
        stage,
        path=path,
        metadata={"evidence_key": evidence_key},
        project_root=str(root),
    )


def test_stage_readiness_without_workflow_state_is_blocked(tmp_path):
    readiness = build_stage_readiness(str(tmp_path))

    assert readiness["readiness_status"] == "blocked"
    assert readiness["stage"] == "literature_review"
    assert readiness["blockers"][0]["code"] == "missing_workflow_state"
    assert readiness["actions"][0]["action"] == "record_evidence_artifact"
    assert any(action["action"] == "initialize_workflow" for action in readiness["actions"])


def test_stage_readiness_reports_missing_evidence_for_current_stage(tmp_path):
    init_workflow("custom", "proposal", project_root=str(tmp_path))
    update_stage("proposal", "in_progress", project_root=str(tmp_path))

    readiness = build_stage_readiness(str(tmp_path))

    assert readiness["stage"] == "proposal"
    assert readiness["readiness_status"] == "incomplete"
    assert readiness["evidence"]["required_count"] == 5
    assert readiness["evidence"]["missing_count"] == 5
    assert readiness["actions"][0]["action"] == "record_evidence_artifact"


def test_computation_readiness_points_missing_evidence_to_generic_intake(tmp_path):
    init_workflow("custom", "computation", project_root=str(tmp_path))

    readiness = build_stage_readiness(str(tmp_path), stage="computation")

    assert readiness["readiness_status"] == "incomplete"
    assert readiness["actions"][0]["action"] == "record_computation_evidence"
    assert {action["action"] for action in readiness["actions"]} == {"record_computation_evidence"}


def test_analysis_readiness_points_missing_evidence_to_generic_intake(tmp_path):
    init_workflow("custom", "analysis_visualization", project_root=str(tmp_path))

    readiness = build_stage_readiness(str(tmp_path), stage="analysis_visualization")

    assert readiness["readiness_status"] == "incomplete"
    assert readiness["actions"][0]["action"] == "record_analysis_evidence"
    assert {action["action"] for action in readiness["actions"]} == {"record_analysis_evidence"}


def test_evidence_matches_by_type_name_and_metadata(tmp_path):
    init_workflow("custom", "proposal", project_root=str(tmp_path))
    for rel_path in [
        "proposal/proposal.md",
        "proposal/calculation_plan.json",
        "proposal/rationale.json",
        "proposal/resource.md",
        "proposal/risk.md",
    ]:
        _write(tmp_path, rel_path)

    register_artifact("proposal.md", "notes", "proposal", path="proposal/proposal.md", project_root=str(tmp_path))
    register_artifact(
        "plan.json",
        "calculation_plan",
        "proposal",
        path="proposal/calculation_plan.json",
        project_root=str(tmp_path),
    )
    register_artifact(
        "rationale.json",
        "custom",
        "proposal",
        path="proposal/rationale.json",
        metadata={"evidence_key": "parameter_rationale"},
        project_root=str(tmp_path),
    )
    register_artifact(
        "resource.md",
        "custom",
        "proposal",
        path="proposal/resource.md",
        metadata={"evidence_keys": ["resource_estimate"]},
        project_root=str(tmp_path),
    )
    register_artifact("risk_register.md", "custom", "proposal", path="proposal/risk.md", project_root=str(tmp_path))

    readiness = build_stage_readiness(str(tmp_path), stage="proposal")

    assert readiness["readiness_status"] == "ready"
    assert readiness["evidence"]["present_count"] == 5
    assert readiness["evidence"]["missing_count"] == 0


def test_completed_stage_requires_checkpoint(tmp_path):
    workflow = init_workflow("custom", "literature_review", project_root=str(tmp_path))
    for evidence_key in [
        "search_log",
        "paper_notes",
        "screening_record",
        "citation_map",
        "review_summary",
        "gaps_and_open_questions",
    ]:
        _register_evidence(tmp_path, "literature_review", evidence_key)
    update_stage("literature_review", "completed", project_root=str(tmp_path))

    blocked = build_stage_readiness(str(tmp_path), stage="literature_review")
    assert blocked["readiness_status"] == "blocked"
    assert {blocker["code"] for blocker in blocked["blockers"]} == {"missing_checkpoint"}

    checkpoint = create_checkpoint(
        workflow["workflow_id"],
        "literature_review",
        "Literature evidence complete",
        project_root=str(tmp_path),
    )
    ready = build_stage_readiness(str(tmp_path), stage="literature_review")
    assert ready["readiness_status"] == "ready"
    assert ready["checkpoint"]["present"] is True
    assert ready["checkpoint"]["checkpoint_id"] == checkpoint["checkpoint_id"]
    assert checkpoint["checkpoint_id"].startswith("ckpt_")


def test_missing_artifact_path_and_lineage_parent_block_readiness(tmp_path):
    init_workflow("custom", "analysis_visualization", project_root=str(tmp_path))
    register_artifact(
        "analysis_report.json",
        "analysis_outputs",
        "analysis_visualization",
        path="analysis/missing_report.json",
        parent_artifacts=["art_missing_parent"],
        metadata={"evidence_key": "analysis_outputs"},
        project_root=str(tmp_path),
    )

    readiness = build_stage_readiness(str(tmp_path), stage="analysis_visualization")

    assert readiness["readiness_status"] == "blocked"
    blocker_codes = {blocker["code"] for blocker in readiness["blockers"]}
    assert "missing_artifact_paths" in blocker_codes
    assert "missing_lineage_parents" in blocker_codes


def test_computation_real_submit_evidence_requires_approved_gate(tmp_path):
    init_workflow("custom", "computation", project_root=str(tmp_path))
    for evidence_key in [
        "calculation_manifest",
        "input_files",
        "input_validation_report",
        "dry_run_report",
        "resource_estimate",
        "credential_scan",
    ]:
        _register_evidence(tmp_path, "computation", evidence_key)
    _write(tmp_path, "computation/job_record.json")
    register_artifact(
        "job_record.json",
        "job_record_if_submitted",
        "computation",
        path="computation/job_record.json",
        metadata={"real_submit": True},
        project_root=str(tmp_path),
    )

    blocked = build_stage_readiness(str(tmp_path), stage="computation")
    assert blocked["readiness_status"] == "blocked"
    assert "missing_hpc_submit_approval" in {blocker["code"] for blocker in blocked["blockers"]}

    decision = record_gate_decision(
        "hpc_submit",
        "approved",
        {"reason": "reviewed dry-run evidence"},
        agent="tester",
        project_root=str(tmp_path),
    )
    ready = build_stage_readiness(str(tmp_path), stage="computation")
    assert ready["readiness_status"] == "ready"
    assert ready["approval"]["hpc_submit_decision"]["decision_id"] == decision["decision_id"]


def test_computation_job_record_is_conditional_for_dry_run_only_evidence(tmp_path):
    init_workflow("custom", "computation", project_root=str(tmp_path))
    for evidence_key in [
        "calculation_manifest",
        "input_files",
        "input_validation_report",
        "dry_run_report",
        "resource_estimate",
        "credential_scan",
    ]:
        _register_evidence(tmp_path, "computation", evidence_key)

    readiness = build_stage_readiness(str(tmp_path), stage="computation")
    job_record = next(
        item for item in readiness["evidence"]["items"]
        if item["evidence_key"] == "job_record_if_submitted"
    )

    assert readiness["readiness_status"] == "ready"
    assert readiness["evidence"]["required_count"] == 6
    assert readiness["evidence"]["missing_count"] == 0
    assert job_record["required"] is False
    assert job_record["required_when"] == "real_submit_recorded"


def test_computation_real_submit_marker_requires_job_record_evidence(tmp_path):
    init_workflow("custom", "computation", project_root=str(tmp_path))
    for evidence_key in [
        "calculation_manifest",
        "input_files",
        "input_validation_report",
        "dry_run_report",
        "resource_estimate",
        "credential_scan",
    ]:
        _register_evidence(tmp_path, "computation", evidence_key)
    _write(tmp_path, "computation/submit_marker.json")
    register_artifact(
        "submit_marker.json",
        "submit_marker",
        "computation",
        path="computation/submit_marker.json",
        metadata={"real_submit": True},
        project_root=str(tmp_path),
    )

    readiness = build_stage_readiness(str(tmp_path), stage="computation")
    job_record = next(
        item for item in readiness["evidence"]["items"]
        if item["evidence_key"] == "job_record_if_submitted"
    )

    assert readiness["readiness_status"] == "blocked"
    assert readiness["evidence"]["required_count"] == 7
    assert job_record["required"] is True
    assert job_record["present"] is False
    assert "missing_hpc_submit_approval" in {blocker["code"] for blocker in readiness["blockers"]}


def test_computation_credential_scan_is_required_evidence(tmp_path):
    init_workflow("custom", "computation", project_root=str(tmp_path))
    for evidence_key in [
        "calculation_manifest",
        "input_files",
        "input_validation_report",
        "dry_run_report",
        "resource_estimate",
    ]:
        _register_evidence(tmp_path, "computation", evidence_key)

    readiness = build_stage_readiness(str(tmp_path), stage="computation")
    missing = {
        item["evidence_key"]
        for item in readiness["evidence"]["items"]
        if item["required"] and not item["present"]
    }

    assert readiness["readiness_status"] == "incomplete"
    assert missing == {"credential_scan"}
    assert {action["action"] for action in readiness["actions"]} == {"record_computation_evidence"}


def test_project_readiness_aggregates_stage_actions(tmp_path):
    init_workflow("custom", "proposal", project_root=str(tmp_path))
    update_stage("proposal", "in_progress", project_root=str(tmp_path))

    readiness = build_project_readiness(str(tmp_path))

    assert readiness["readiness_status"] == "incomplete"
    assert [stage["stage"] for stage in readiness["stages"]] == [
        "literature_review",
        "proposal",
        "modeling",
        "computation",
        "analysis_visualization",
        "writing",
    ]
    assert any(action["stage"] == "proposal" for action in readiness["actions"])
