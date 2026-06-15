#!/usr/bin/env python3
"""E2E exercises for MLP-MD readiness gates and recovery paths."""

import json
from pathlib import Path

from runtime.simflow_core.gates import check_gate, record_gate_decision
from runtime.simflow_core.checkpoints import restore_checkpoint
from runtime.simflow_core.state import init_workflow, read_state
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
            "execution_gate": {"status": "approval_required", "gate": "production_md_readiness"},
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
        "approval_present",
    ]
    assert read_state(project_root=str(tmp_path), state_file="jobs.json") == []

    _write_production_md_readiness_evidence(tmp_path, validation_status="missing")
    missing_validation = check_gate("production_md_readiness", {"project_root": str(tmp_path)})
    assert missing_validation["status"] == "block"
    assert "validation_passed" in missing_validation["conditions"]["unmet"]

    _write_production_md_readiness_evidence(tmp_path, anomaly_thresholds_defined=False)
    blocked = check_gate("production_md_readiness", {"project_root": str(tmp_path)})
    assert blocked["status"] == "block"
    assert "anomaly_thresholds_defined" in blocked["conditions"]["unmet"]


def test_tracked_only_checkpoint_recovery_resumes_after_evidence_intake(tmp_path):
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
    assert warning["status"] == "capability_warning"
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
