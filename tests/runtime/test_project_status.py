#!/usr/bin/env python3
"""Tests for read-only SimFlow project status summaries."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "runtime"))

from runtime.simflow_core.artifacts import register_artifact
from runtime.simflow_core.checkpoints import create_checkpoint
from runtime.simflow_core.gates import record_gate_decision
from runtime.simflow_core.state import init_workflow, update_stage
from runtime.simflow_core.status import (
    build_evidence_graph,
    build_handoff_summary,
    build_project_status,
)
from runtime.simflow_core.verification import persist_verification_state


def _write(root: Path, relative_path: str, content: str = "content\n") -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_project_status_reports_progress_risks_and_next_action(tmp_path):
    workflow = init_workflow("custom", "literature_review", project_root=str(tmp_path))
    update_stage("literature_review", "completed", project_root=str(tmp_path))
    update_stage("proposal", "in_progress", project_root=str(tmp_path))
    checkpoint = create_checkpoint(
        workflow["workflow_id"],
        "literature_review",
        "Literature review complete",
        project_root=str(tmp_path),
    )

    _write(tmp_path, "literature/review.md")
    literature = register_artifact(
        "review.md",
        "review_summary",
        "literature_review",
        path="literature/review.md",
        project_root=str(tmp_path),
    )
    _write(tmp_path, "proposal/plan.md")
    register_artifact(
        "plan.md",
        "proposal_plan",
        "proposal",
        path="proposal/plan.md",
        parent_artifacts=[literature["artifact_id"]],
        project_root=str(tmp_path),
    )
    register_artifact(
        "missing.csv",
        "analysis_table",
        "analysis_visualization",
        path="analysis/missing.csv",
        project_root=str(tmp_path),
    )
    register_artifact(
        "orphan.md",
        "derived_note",
        "writing",
        path=None,
        parent_artifacts=["art_missing_parent"],
        project_root=str(tmp_path),
    )
    decision = record_gate_decision(
        "hpc_submit",
        "approved",
        {"source": "test"},
        agent="tester",
        project_root=str(tmp_path),
    )

    status = build_project_status(str(tmp_path))

    assert status["workflow"]["workflow_id"] == workflow["workflow_id"]
    assert status["progress"]["completed_stages"] == ["literature_review"]
    assert status["progress"]["progress_pct"] == 16.7
    assert status["next_actions"] == [
        {"action": "continue_stage", "stage": "proposal", "reason": "stage_in_progress"}
    ]
    assert status["artifacts"]["total"] == 4
    assert status["artifacts"]["by_stage"]["proposal"] == 1
    assert status["checkpoints"]["latest"]["checkpoint_id"] == checkpoint["checkpoint_id"]
    assert status["gates"]["latest_decisions"]["hpc_submit"]["latest_decision_id"] == decision["decision_id"]

    risk_codes = {risk["code"] for risk in status["risks"]}
    assert "missing_artifact_paths" in risk_codes
    assert "missing_lineage_parents" in risk_codes


def test_evidence_graph_filters_stage_and_artifact(tmp_path):
    init_workflow("custom", "literature_review", project_root=str(tmp_path))
    _write(tmp_path, "literature/review.md")
    parent = register_artifact(
        "review.md",
        "review_summary",
        "literature_review",
        path="literature/review.md",
        project_root=str(tmp_path),
    )
    _write(tmp_path, "proposal/plan.md")
    child = register_artifact(
        "plan.md",
        "proposal_plan",
        "proposal",
        path="proposal/plan.md",
        parent_artifacts=[parent["artifact_id"]],
        project_root=str(tmp_path),
    )

    proposal_graph = build_evidence_graph(str(tmp_path), stage="proposal")
    assert [node["artifact_id"] for node in proposal_graph["nodes"]] == [child["artifact_id"]]
    assert proposal_graph["links"] == []

    artifact_graph = build_evidence_graph(str(tmp_path), artifact_id=child["artifact_id"])
    node_ids = {node["artifact_id"] for node in artifact_graph["nodes"]}
    assert node_ids == {parent["artifact_id"], child["artifact_id"]}
    assert artifact_graph["links"] == [
        {
            "child_artifact_id": child["artifact_id"],
            "parent_artifact_id": parent["artifact_id"],
            "relationship": "derived_from",
            "stage": "proposal",
        }
    ]


def test_evidence_graph_filters_helper_evidence_metadata(tmp_path):
    init_workflow("custom", "analysis_visualization", project_root=str(tmp_path))
    _write(tmp_path, "analysis/gpumd_parse.json")
    _write(tmp_path, "analysis/lammps_inspect.json")
    gpumd = register_artifact(
        "gpumd_parse.json",
        "helper_output",
        "analysis_visualization",
        path="analysis/gpumd_parse.json",
        software="gpumd",
        metadata={
            "schema_version": "simflow.helper_evidence.v1",
            "helper": "parse_gpumd_outputs",
            "evidence_role": "gpumd_nep_output_parse_summary",
            "status": "warning",
            "parser_status": "partial",
            "actual_tool_used": {"name": "gpumd", "support_level": "helper_supported"},
        },
        project_root=str(tmp_path),
    )
    register_artifact(
        "lammps_inspect.json",
        "helper_output",
        "analysis_visualization",
        path="analysis/lammps_inspect.json",
        software="lammps",
        metadata={
            "schema_version": "simflow.helper_evidence.v1",
            "helper": "lammps_inspect_inputs",
            "evidence_role": "lammps_input_inspection",
            "status": "success",
            "parser_status": "parsed",
            "actual_tool_used": {"name": "lammps", "support_level": "helper_supported"},
        },
        project_root=str(tmp_path),
    )

    graph = build_evidence_graph(
        str(tmp_path),
        evidence_role="gpumd_nep_output_parse_summary",
        tool="gpumd",
        status="warning",
        schema_version="simflow.helper_evidence.v1",
    )

    assert [node["artifact_id"] for node in graph["nodes"]] == [gpumd["artifact_id"]]
    assert graph["nodes"][0]["helper"] == "parse_gpumd_outputs"
    assert graph["nodes"][0]["helper_status"] == "warning"
    assert graph["nodes"][0]["parser_status"] == "partial"
    assert graph["nodes"][0]["actual_tool_used"]["support_level"] == "helper_supported"


def test_evidence_graph_v2_filters_recipe_claim_and_depth(tmp_path):
    init_workflow("mlp_md", "analysis_visualization", project_root=str(tmp_path))
    _write(tmp_path, "analysis/dataset.json")
    _write(tmp_path, "compute/training.json")
    _write(tmp_path, "analysis/metrics.json")
    _write(
        tmp_path,
        "writing/claim_map.json",
        '{"claims": [{"claim_id": "claim_metrics", "source_artifact_ids": []}]}\n',
    )
    dataset = register_artifact(
        "dataset.json",
        "helper_output",
        "analysis_visualization",
        path="analysis/dataset.json",
        metadata={"recipe": "mlp_md", "evidence_role": "dataset_manifest"},
        project_root=str(tmp_path),
    )
    training = register_artifact(
        "training.json",
        "helper_output",
        "computation",
        path="compute/training.json",
        parent_artifacts=[dataset["artifact_id"]],
        metadata={"recipe": "mlp_md", "evidence_role": "training_run_manifest"},
        project_root=str(tmp_path),
    )
    metrics = register_artifact(
        "metrics.json",
        "helper_output",
        "analysis_visualization",
        path="analysis/metrics.json",
        parent_artifacts=[training["artifact_id"]],
        metadata={"recipe": "mlp_md", "evidence_role": "model_metrics_summary"},
        project_root=str(tmp_path),
    )
    claim_path = tmp_path / "writing" / "claim_map.json"
    claim_path.write_text(
        '{"claims": [{"claim_id": "claim_metrics", "source_artifact_ids": ["'
        + metrics["artifact_id"]
        + '"]}]}\n',
        encoding="utf-8",
    )
    claim_map = register_artifact(
        "claim_map.json",
        "claim_map",
        "writing",
        path="writing/claim_map.json",
        parent_artifacts=[metrics["artifact_id"]],
        metadata={"recipe": "mlp_md", "claim_ids": ["claim_metrics"]},
        project_root=str(tmp_path),
    )

    graph = build_evidence_graph(
        str(tmp_path),
        recipe="mlp_md",
        claim_id="claim_metrics",
        direction="upstream",
        depth=2,
    )
    node_ids = {node["artifact_id"] for node in graph["nodes"]}

    assert {dataset["artifact_id"], training["artifact_id"], metrics["artifact_id"], claim_map["artifact_id"]}.issubset(node_ids)
    assert graph["filters"]["direction"] == "upstream"
    assert graph["filters"]["depth"] == 2
    assert graph["query_limits"]["max_depth"] == 5


def test_handoff_summary_is_compact_and_read_only(tmp_path):
    workflow = init_workflow("custom", "literature_review", project_root=str(tmp_path))
    update_stage("literature_review", "completed", project_root=str(tmp_path))
    checkpoint = create_checkpoint(
        workflow["workflow_id"],
        "literature_review",
        "Literature review complete",
        project_root=str(tmp_path),
    )

    summary = build_handoff_summary(str(tmp_path))

    assert summary["workflow"]["workflow_id"] == workflow["workflow_id"]
    assert summary["completed_stages"] == ["literature_review"]
    assert summary["latest_checkpoint"]["checkpoint_id"] == checkpoint["checkpoint_id"]
    assert "artifact_summary" in summary
    assert "readiness" in summary
    assert not (tmp_path / ".simflow" / "reports" / "handoff").exists()


def test_project_status_surfaces_generic_evidence_intake_actions(tmp_path):
    init_workflow("custom", "computation", project_root=str(tmp_path))
    update_stage("computation", "waiting", project_root=str(tmp_path))
    update_stage("analysis_visualization", "waiting", project_root=str(tmp_path))

    status = build_project_status(str(tmp_path))
    actions = status["readiness"]["generic_evidence_actions"]

    assert status["readiness"]["readiness_status"] == "incomplete"
    assert {
        (action["action"], action.get("stage"))
        for action in actions
    } >= {
        ("record_computation_evidence", "computation"),
        ("record_analysis_evidence", "analysis_visualization"),
    }

    computation = next(stage for stage in status["readiness"]["stages"] if stage["stage"] == "computation")
    analysis = next(stage for stage in status["readiness"]["stages"] if stage["stage"] == "analysis_visualization")
    assert computation["stage_status"] == "waiting"
    assert computation["missing_evidence"] > 0
    assert analysis["stage_status"] == "waiting"
    assert analysis["missing_evidence"] > 0

    handoff = build_handoff_summary(str(tmp_path))
    assert handoff["readiness"]["generic_evidence_actions"] == actions


def test_project_status_without_workflow_state_reports_risk(tmp_path):
    status = build_project_status(str(tmp_path))

    assert status["workflow"]["status"] == "missing"
    risk_codes = {risk["code"] for risk in status["risks"]}
    assert {"missing_workflow_state", "missing_checkpoint"}.issubset(risk_codes)
    assert status["next_actions"][0]["action"] == "start_stage"


def test_project_status_preserves_list_backed_verification_reports(tmp_path):
    workflow = init_workflow("custom", "writing", project_root=str(tmp_path))
    report = {
        "stage": "writing",
        "workflow_id": workflow["workflow_id"],
        "status": "warning",
        "generated_at": "2026-07-11T00:00:00+00:00",
        "completed_at": "2026-07-11T00:05:00+00:00",
        "checks": [
            {
                "name": "traceability",
                "status": "warning",
                "message": "missing provenance appendix",
                "details": {},
                "checked_at": "2026-07-11T00:05:00+00:00",
            }
        ],
        "warnings": ["missing provenance appendix"],
        "failures": [],
        "source_artifact_ids": ["art_1234abcd"],
    }
    persist_verification_state(report, project_root=str(tmp_path))

    status = build_project_status(str(tmp_path))

    assert isinstance(status["verification"], list)
    assert status["verification"] == [report]
