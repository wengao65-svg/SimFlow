#!/usr/bin/env python3
"""E2E exercises for MLP-MD readiness gates and recovery paths."""

import json
from pathlib import Path

from runtime.simflow_core.artifacts import register_artifact
from runtime.simflow_core.gates import check_gate, record_gate_decision
from runtime.simflow_core.checkpoints import restore_checkpoint
from runtime.simflow_core.helper_evidence import build_helper_evidence
from runtime.simflow_core.state import init_workflow, read_state
from runtime.simflow_core.status import build_evidence_graph
from runtime.simflow_helpers.computation.evidence_intake import record_computation_evidence
from runtime.simflow_helpers.project.intake import init_research
from runtime.simflow_helpers.stages.pipeline import run_pipeline


def _write_json(path: Path, payload: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(path)


def _write_text(path: Path, text: str = "{}\n") -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return str(path)


def _relative(root: Path, path: str) -> str:
    return str(Path(path).resolve().relative_to(root.resolve()))


def _write_production_md_readiness_evidence(
    project_root: Path,
    *,
    anomaly_thresholds_defined: bool = True,
    validation_status: str = "pass",
) -> None:
    artifacts = project_root / ".simflow" / "artifacts"
    _write_json(
        artifacts / "analysis" / "dataset_manifest.json",
        {"recipe": "mlp_md", "lineage_complete": True, "round": "round_000"},
    )
    _write_json(
        artifacts / "analysis" / "labeling_manifest.json",
        {"recipe": "mlp_md", "status": "completed", "label_source": "synthetic_dft_fixture"},
    )
    _write_json(
        artifacts / "compute" / "training_run_manifest.json",
        {"recipe": "mlp_md", "status": "completed", "model_artifact": "nep.txt"},
    )
    _write_json(
        artifacts / "analysis" / "model_metrics_summary.json",
        {"recipe": "mlp_md", "status": "success", "force_rmse": 0.05},
    )
    _write_json(
        artifacts / "analysis" / "model_validation_report.json",
        {"recipe": "mlp_md", "status": validation_status, "rmse_energy_mev_atom": 5.0},
    )
    _write_json(
        artifacts / "compute" / "smoke_md_manifest.json",
        {"recipe": "mlp_md", "smoke_status": "pass", "steps": 1000},
    )
    _write_json(
        artifacts / "analysis" / "anomaly_report.json",
        {"recipe": "mlp_md", "thresholds_defined": anomaly_thresholds_defined},
    )
    _write_json(
        artifacts / "analysis" / "active_learning_round_manifest.json",
        {"recipe": "mlp_md", "status": "completed", "round": "round_000"},
    )
    _write_json(
        artifacts / "analysis" / "production_md_readiness_report.json",
        {
            "recipe": "mlp_md",
            "scientific_readiness": {"status": "ready"},
            "production_md_gate_approved": False,
            "execution_gate": {
                "status": "approval_required",
                "gate": "production_md_readiness",
                "gate_scope": "production_md_readiness_only",
                "production_md_gate_approved": False,
                "real_submit_allowed": False,
            },
            "real_submit_gate": {
                "gate": "hpc_submit",
                "status": "required_for_real_submit",
            },
            "real_submit_allowed": False,
        },
    )


def _tracked_only_evidence(project_root: Path) -> dict:
    base = project_root / "user_compute"
    return {
        "calculation_manifest": _relative(project_root, _write_text(base / "calculation_manifest.json")),
        "input_files": [_relative(project_root, _write_text(base / "run.in"))],
        "input_validation_report": _relative(project_root, _write_text(base / "input_validation.json")),
        "dry_run_report": _relative(project_root, _write_text(base / "dry_run_report.json")),
        "resource_estimate": _relative(project_root, _write_text(base / "resource_estimate.json")),
        "credential_scan": _relative(project_root, _write_text(base / "credential_scan.json")),
    }


def _register_mlp_helper_artifact(
    project_root: Path,
    *,
    name: str,
    stage: str,
    role: str,
    payload: dict,
    parents: list[str] | None = None,
    status: str = "success",
    parser_status: str = "parsed",
) -> dict:
    relative_path = f".simflow/artifacts/{stage}/{name}"
    _write_json(project_root / relative_path, payload)
    evidence = build_helper_evidence(
        helper="synthetic_mlp_fixture",
        capability=role,
        status=status,
        stage=stage,
        activity=role,
        evidence_role=role,
        source_files=[],
        actual_tool_used={"software": "custom", "support_level": "tracked_only"},
        parser_status=parser_status,
        claim_limits=[
            "Synthetic fixture evidence supports provenance and gate behavior tests only.",
            "No model quality, transferability, or production execution claim is made.",
        ],
        recipe="mlp_md",
        parent_artifacts=parents or [],
    )
    return register_artifact(
        name,
        "helper_output",
        stage,
        path=relative_path,
        parent_artifacts=parents or [],
        metadata=evidence,
        project_root=str(project_root),
    )


def _register_synthetic_mlp_evidence_graph(project_root: Path) -> dict[str, dict]:
    dataset = _register_mlp_helper_artifact(
        project_root,
        name="dataset_manifest.json",
        stage="analysis_visualization",
        role="dataset_manifest",
        payload={"recipe": "mlp_md", "lineage_complete": True, "split": "train"},
    )
    labeling = _register_mlp_helper_artifact(
        project_root,
        name="labeling_manifest.json",
        stage="analysis_visualization",
        role="labeling_manifest",
        payload={"recipe": "mlp_md", "status": "completed", "label_source": "synthetic_dft_fixture"},
        parents=[dataset["artifact_id"]],
    )
    training = _register_mlp_helper_artifact(
        project_root,
        name="training_run_manifest.json",
        stage="computation",
        role="training_run_manifest",
        payload={"recipe": "mlp_md", "status": "completed", "model_artifact": "synthetic_nep.txt"},
        parents=[dataset["artifact_id"], labeling["artifact_id"]],
    )
    metrics = _register_mlp_helper_artifact(
        project_root,
        name="model_metrics_summary.json",
        stage="analysis_visualization",
        role="model_metrics_summary",
        payload={"recipe": "mlp_md", "status": "success", "force_rmse": 0.05},
        parents=[training["artifact_id"]],
    )
    validation = _register_mlp_helper_artifact(
        project_root,
        name="model_validation_report.json",
        stage="analysis_visualization",
        role="model_validation_report",
        payload={"recipe": "mlp_md", "status": "pass", "validation_domain": "synthetic_holdout"},
        parents=[training["artifact_id"], metrics["artifact_id"]],
    )
    smoke = _register_mlp_helper_artifact(
        project_root,
        name="smoke_md_manifest.json",
        stage="computation",
        role="smoke_md_manifest",
        payload={"recipe": "mlp_md", "smoke_status": "pass", "steps": 1000},
        parents=[training["artifact_id"]],
    )
    anomaly = _register_mlp_helper_artifact(
        project_root,
        name="anomaly_report.json",
        stage="analysis_visualization",
        role="anomaly_report",
        payload={"recipe": "mlp_md", "thresholds_defined": True},
        parents=[validation["artifact_id"], smoke["artifact_id"]],
    )
    active_learning = _register_mlp_helper_artifact(
        project_root,
        name="active_learning_round_manifest.json",
        stage="analysis_visualization",
        role="active_learning_round_manifest",
        payload={"recipe": "mlp_md", "status": "completed", "round": "round_000"},
        parents=[anomaly["artifact_id"]],
    )
    readiness = _register_mlp_helper_artifact(
        project_root,
        name="production_md_readiness_report.json",
        stage="analysis_visualization",
        role="production_md_readiness_report",
        payload={
            "recipe": "mlp_md",
            "scientific_readiness": {"status": "ready"},
            "production_md_gate_approved": False,
            "execution_gate": {
                "status": "approval_required",
                "gate": "production_md_readiness",
                "gate_scope": "production_md_readiness_only",
                "missing_roles": ["approval_record"],
                "production_md_gate_approved": False,
                "real_submit_allowed": False,
            },
            "real_submit_gate": {
                "gate": "hpc_submit",
                "status": "required_for_real_submit",
            },
            "real_submit_allowed": False,
        },
        parents=[validation["artifact_id"], smoke["artifact_id"], anomaly["artifact_id"], active_learning["artifact_id"]],
    )
    claim_path = ".simflow/reports/writing/claim_map.json"
    _write_json(
        project_root / claim_path,
        {
            "claims": [
                {
                    "claim_id": "claim_production_ready",
                    "status": "approval_required",
                    "source_artifact_ids": [readiness["artifact_id"]],
                },
                {
                    "claim_id": "claim_metrics",
                    "status": "supported",
                    "source_artifact_ids": [metrics["artifact_id"]],
                },
            ],
        },
    )
    claim_map = register_artifact(
        "claim_map.json",
        "claim_map",
        "writing",
        path=claim_path,
        parent_artifacts=[readiness["artifact_id"], metrics["artifact_id"]],
        metadata={"recipe": "mlp_md", "claim_ids": ["claim_production_ready", "claim_metrics"]},
        project_root=str(project_root),
    )
    return {
        "dataset": dataset,
        "labeling": labeling,
        "training": training,
        "metrics": metrics,
        "validation": validation,
        "smoke": smoke,
        "anomaly": anomaly,
        "active_learning": active_learning,
        "readiness": readiness,
        "claim_map": claim_map,
    }


def test_mlp_md_production_readiness_gate_passes_and_blocks_from_fixture(tmp_path):
    init_workflow("mlp_md", "analysis_visualization", project_root=str(tmp_path))
    _write_production_md_readiness_evidence(tmp_path)

    before_approval = check_gate("production_md_readiness", {"project_root": str(tmp_path)})
    assert before_approval["status"] == "block"
    assert "readiness_report_ready" in before_approval["conditions"]["met"]
    assert "approval_present" in before_approval["conditions"]["unmet"]

    record_gate_decision(
        "production_md_readiness",
        "approved",
        {"reason": "reviewed MLP-MD validation and long-MD smoke evidence"},
        project_root=str(tmp_path),
        agent="pytest",
    )
    approved = check_gate("production_md_readiness", {"project_root": str(tmp_path)})
    assert approved["status"] == "pass"
    assert approved["conditions"]["met"] == [
        "dataset_lineage_complete",
        "labeling_completed",
        "training_completed",
        "metrics_summary_present",
        "validation_passed",
        "smoke_md_passed",
        "anomaly_thresholds_defined",
        "active_learning_round_reviewed",
        "readiness_report_ready",
        "readiness_does_not_authorize_submit",
        "approval_present",
    ]
    assert read_state(project_root=str(tmp_path), state_file="jobs.json") == []
    submit_gate = check_gate("hpc_submit", {"project_root": str(tmp_path)})
    assert submit_gate["status"] == "block"
    assert "dry_run_passed" in submit_gate["conditions"]["unmet"]

    _write_production_md_readiness_evidence(tmp_path, validation_status="missing")
    missing_validation = check_gate("production_md_readiness", {"project_root": str(tmp_path)})
    assert missing_validation["status"] == "block"
    assert "validation_passed" in missing_validation["conditions"]["unmet"]

    _write_production_md_readiness_evidence(tmp_path, anomaly_thresholds_defined=False)
    blocked = check_gate("production_md_readiness", {"project_root": str(tmp_path)})
    assert blocked["status"] == "block"
    assert "anomaly_thresholds_defined" in blocked["conditions"]["unmet"]


def test_gpumd_needs_inputs_checkpoint_recovery_resumes_after_evidence_intake(tmp_path):
    init_research(
        input_text="\n".join([
            "entry_stage: modeling",
            "goal: recover a GPUMD NEP tracked-only workflow",
            "method: mlp_md",
            "material: Si",
            "software: gpumd",
            "toolchain: gpumd, nep",
            "parameters: {\"structure_type\": \"diamond\", \"lattice_param\": 5.43, \"elements\": [\"Si\"]}",
        ]),
        output_dir=str(tmp_path),
    )

    warning = run_pipeline(str(tmp_path / ".simflow"), target_stage="computation", dry_run=False)
    assert warning["status"] == "needs_inputs"
    assert read_state(project_root=str(tmp_path), state_file="stages.json")["computation"]["status"] == "waiting"

    intake = record_computation_evidence(
        str(tmp_path / ".simflow"),
        params={
            "software": "gpumd",
            "task": "nep_training",
            "command": "gpumd < run.in",
            "complete_stage": True,
            "evidence": _tracked_only_evidence(tmp_path),
        },
    )
    assert intake["status"] == "success"
    assert intake["stage_completed"] is True
    assert intake["checkpoint_id"]

    workflow = read_state(project_root=str(tmp_path), state_file="workflow.json")
    workflow["status"] = "corrupted_after_intake"
    from runtime.simflow_core.state import write_state

    write_state(workflow, project_root=str(tmp_path), state_file="workflow.json")
    assert read_state(project_root=str(tmp_path), state_file="workflow.json")["status"] == "corrupted_after_intake"

    restored = restore_checkpoint(intake["checkpoint_id"], project_root=str(tmp_path))
    assert restored is not None
    assert read_state(project_root=str(tmp_path), state_file="stages.json")["computation"]["status"] == "completed"

    rerun = run_pipeline(str(tmp_path / ".simflow"), target_stage="computation", dry_run=False)
    assert rerun["status"] == "success"
    assert rerun["stages_executed"] == 0


def test_mlp_md_evidence_graph_traces_readiness_claim_to_synthetic_fixture(tmp_path):
    init_workflow("mlp_md", "analysis_visualization", project_root=str(tmp_path))
    artifacts = _register_synthetic_mlp_evidence_graph(tmp_path)

    graph = build_evidence_graph(
        str(tmp_path),
        recipe="mlp_md",
        claim_id="claim_production_ready",
        direction="upstream",
        depth=5,
    )
    node_ids = {node["artifact_id"] for node in graph["nodes"]}

    assert {
        artifacts["dataset"]["artifact_id"],
        artifacts["labeling"]["artifact_id"],
        artifacts["training"]["artifact_id"],
        artifacts["metrics"]["artifact_id"],
        artifacts["validation"]["artifact_id"],
        artifacts["smoke"]["artifact_id"],
        artifacts["anomaly"]["artifact_id"],
        artifacts["active_learning"]["artifact_id"],
        artifacts["readiness"]["artifact_id"],
        artifacts["claim_map"]["artifact_id"],
    }.issubset(node_ids)
    readiness_node = next(node for node in graph["nodes"] if node["artifact_id"] == artifacts["readiness"]["artifact_id"])
    assert readiness_node["evidence_role"] == "production_md_readiness_report"
    assert readiness_node["recipe"] == "mlp_md"
    assert graph["filters"]["claim_id"] == "claim_production_ready"
    assert graph["query_limits"]["claim_id_policy"].startswith("Matches only explicit")

    metrics_graph = build_evidence_graph(
        str(tmp_path),
        recipe="mlp_md",
        claim_id="claim_metrics",
        direction="upstream",
        depth=3,
    )
    metrics_node_ids = {node["artifact_id"] for node in metrics_graph["nodes"]}
    assert artifacts["metrics"]["artifact_id"] in metrics_node_ids
    assert artifacts["training"]["artifact_id"] in metrics_node_ids
    assert artifacts["dataset"]["artifact_id"] in metrics_node_ids
