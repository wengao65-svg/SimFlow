#!/usr/bin/env python3
"""Tests for generic computation evidence intake."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from runtime.simflow_core.artifacts import list_artifacts
from runtime.simflow_core.state import read_state
from runtime.simflow_helpers.computation.evidence_intake import record_computation_evidence
from runtime.simflow_helpers.project.intake import init_research
from runtime.simflow_helpers.stages.pipeline import run_pipeline


def _write(root: Path, relative_path: str, payload: str = "{}\n") -> str:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
    return relative_path


def _init_gpumd_project(tmp_path: Path) -> None:
    init_research(
        input_text="\n".join([
            "entry_stage: modeling",
            "goal: build GPUMD NEP workflow",
            "method: mlp_md",
            "material: Si",
            "software: gpumd",
            "toolchain: gpumd, nep",
            "parameters: {\"structure_type\": \"diamond\", \"lattice_param\": 5.43, \"elements\": [\"Si\"]}",
        ]),
        output_dir=str(tmp_path),
    )


def _evidence_paths(tmp_path: Path) -> dict:
    return {
        "calculation_manifest": _write(tmp_path, "user_compute/calculation_manifest.json"),
        "input_files": [_write(tmp_path, "user_compute/run.in")],
        "input_validation_report": _write(tmp_path, "user_compute/input_validation.json"),
        "dry_run_report": _write(tmp_path, "user_compute/dry_run_report.json"),
        "resource_estimate": _write(tmp_path, "user_compute/resource_estimate.json"),
    }


def test_record_computation_evidence_completes_tracked_only_waiting_stage(tmp_path):
    _init_gpumd_project(tmp_path)
    warning = run_pipeline(str(tmp_path / ".simflow"), target_stage="computation", dry_run=False)
    assert warning["status"] == "capability_warning"

    result = record_computation_evidence(
        str(tmp_path / ".simflow"),
        params={
            "software": "gpumd",
            "task": "nep_training",
            "command": "gpumd < run.in",
            "version": "user-recorded",
            "environment": {"module": "gpumd"},
            "complete_stage": True,
            "evidence": _evidence_paths(tmp_path),
        },
    )
    stages = read_state(str(tmp_path), "stages.json")
    artifacts = list_artifacts(stage="computation", project_root=str(tmp_path))
    intake_artifact = next(artifact for artifact in artifacts if artifact["type"] == "evidence_intake_manifest")
    manifest = json.loads((tmp_path / intake_artifact["path"]).read_text(encoding="utf-8"))
    rerun = run_pipeline(str(tmp_path / ".simflow"), target_stage="computation", dry_run=False)

    assert result["status"] == "success"
    assert result["stage_completed"] is True
    assert result["checkpoint_id"] is not None
    assert result["readiness"]["readiness_status"] == "ready"
    assert stages["computation"]["status"] == "completed"
    assert stages["computation"]["checkpoint_id"] == result["checkpoint_id"]
    assert manifest["actual_tool_used"]["support_level"] == "tracked_only"
    assert manifest["actual_tool_used"]["name"] == "gpumd"
    assert rerun["status"] == "success"
    assert rerun["stages_executed"] == 0


def test_record_computation_evidence_can_record_without_completing_stage(tmp_path):
    _init_gpumd_project(tmp_path)
    run_pipeline(str(tmp_path / ".simflow"), target_stage="computation", dry_run=False)

    result = record_computation_evidence(
        str(tmp_path / ".simflow"),
        params={
            "software": "gpumd",
            "complete_stage": False,
            "evidence": _evidence_paths(tmp_path),
        },
    )
    stages = read_state(str(tmp_path), "stages.json")

    assert result["status"] == "success"
    assert result["stage_completed"] is False
    assert result["readiness"]["readiness_status"] == "ready"
    assert stages["computation"]["status"] == "waiting"


def test_record_computation_evidence_rejects_missing_paths_without_artifacts(tmp_path):
    _init_gpumd_project(tmp_path)
    before = list_artifacts(stage="computation", project_root=str(tmp_path))

    result = record_computation_evidence(
        str(tmp_path / ".simflow"),
        params={
            "software": "gpumd",
            "evidence": {
                "calculation_manifest": "missing/calculation_manifest.json",
            },
        },
    )
    after = list_artifacts(stage="computation", project_root=str(tmp_path))

    assert result["status"] == "error"
    assert result["missing"] == [
        {"evidence_key": "calculation_manifest", "path": "missing/calculation_manifest.json"}
    ]
    assert after == before


def test_record_computation_evidence_uses_shared_tool_normalization_for_qe(tmp_path):
    init_research(
        input_text="\n".join([
            "entry_stage: computation",
            "goal: record QE dry-run evidence",
            "method: dft",
            "material: Si",
            "software: qe",
        ]),
        output_dir=str(tmp_path),
    )

    result = record_computation_evidence(
        str(tmp_path / ".simflow"),
        params={
            "software": "qe",
            "task": "scf",
            "evidence": _evidence_paths(tmp_path),
        },
    )
    manifest = result["manifest"]

    assert result["status"] == "success"
    assert result["readiness"]["readiness_status"] == "ready"
    assert manifest["actual_tool_used"]["name"] == "quantum_espresso"
    assert manifest["actual_tool_used"]["support_level"] == "tracked_only"
