"""Tests for GPUMD/NEP and generic MLP helper scripts."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HELPER_SCHEMA_VERSION = "simflow.helper_evidence.v1"


def _run(*args: str) -> dict:
    completed = subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(completed.stdout)


def test_inspect_gpumd_inputs_is_static_and_reports_missing_expected_files(tmp_path):
    (tmp_path / "run.in").write_text("potential nep.txt\ncompute thermo\n", encoding="utf-8")

    result = _run(
        "skills/simflow-gpumd/scripts/inspect_gpumd_inputs.py",
        "--calculation-dir",
        str(tmp_path),
    )

    assert result["status"] == "warning"
    assert result["schema_version"] == HELPER_SCHEMA_VERSION
    assert result["helper"] == "inspect_gpumd_inputs"
    assert result["parser_status"] == "not_applicable"
    assert result["claim_limits"]
    assert result["mode"] == "gpumd"
    assert result["capability_support_level"] == "helper_supported"
    assert result["tool_capabilities"]["gpumd"]["tool_support_level"] == "tracked_only"
    assert any(warning["code"] == "missing_expected_file" for warning in result["warnings"])
    assert any(warning["code"] == "missing_referenced_file" for warning in result["warnings"])


def test_build_gpumd_manifest_records_tracked_only_tool_support(tmp_path):
    run_in = tmp_path / "run.in"
    output = tmp_path / "manifest.json"
    run_in.write_text("potential nep.txt\n", encoding="utf-8")

    result = _run(
        "skills/simflow-gpumd/scripts/build_gpumd_manifest.py",
        "--files",
        str(run_in),
        "--output",
        str(output),
        "--software",
        "gpumd",
        "--command",
        "gpumd < run.in",
    )

    assert result["status"] == "success"
    assert result["schema_version"] == HELPER_SCHEMA_VERSION
    assert result["helper"] == "build_gpumd_manifest"
    assert result["parser_status"] == "not_applicable"
    assert result["source_files"][0]["sha256"]
    assert result["capability_support_level"] == "helper_supported"
    assert result["actual_tool_used"]["support_level"] == "tracked_only"
    assert result["tool_support"]["tracked_only"] == ["gpumd", "nep"]
    assert output.is_file()


def test_build_gpumd_manifest_invalid_environment_json_warns_without_crashing(tmp_path):
    run_in = tmp_path / "run.in"
    output = tmp_path / "manifest.json"
    run_in.write_text("potential nep.txt\n", encoding="utf-8")

    result = _run(
        "skills/simflow-gpumd/scripts/build_gpumd_manifest.py",
        "--files",
        str(run_in),
        "--output",
        str(output),
        "--software",
        "gpumd",
        "--environment",
        "{bad-json",
    )

    assert result["status"] == "warning"
    assert result["schema_version"] == HELPER_SCHEMA_VERSION
    assert any(warning["code"] == "invalid_environment_json" for warning in result["warnings"])
    assert result["actual_tool_used"]["environment"] is None


def test_parse_gpumd_outputs_summarizes_numeric_table_without_readiness_claim(tmp_path):
    thermo = tmp_path / "thermo.out"
    thermo.write_text("0 300 1.0\n1 305 1.1\n", encoding="utf-8")

    result = _run(
        "skills/simflow-gpumd/scripts/parse_gpumd_outputs.py",
        "--files",
        str(thermo),
    )

    parsed = result["files"][0]
    assert result["schema_version"] == HELPER_SCHEMA_VERSION
    assert result["helper"] == "parse_gpumd_outputs"
    assert result["parser_status"] == "parsed"
    assert result["source_files"][0]["bytes"] is not None
    assert result["capability_support_level"] == "helper_supported"
    assert parsed["role"] == "thermo_table"
    assert parsed["rows"] == 2
    assert parsed["columns"] == 3
    assert "No convergence" in result["limitations"][1]


def test_parse_gpumd_outputs_marks_missing_file_blocked_with_file_metadata(tmp_path):
    missing = tmp_path / "loss.out"

    result = _run(
        "skills/simflow-gpumd/scripts/parse_gpumd_outputs.py",
        "--files",
        str(missing),
    )

    parsed = result["files"][0]
    assert result["status"] == "blocked"
    assert result["schema_version"] == HELPER_SCHEMA_VERSION
    assert result["parser_status"] == "missing"
    assert parsed["software"] == "nep"
    assert parsed["parser_status"] == "missing"
    assert parsed["sha256"] is None
    assert parsed["bytes"] is None


def test_parse_gpumd_outputs_supports_software_override(tmp_path):
    table = tmp_path / "custom.out"
    table.write_text("step loss\n0 1.0\n", encoding="utf-8")

    result = _run(
        "skills/simflow-gpumd/scripts/parse_gpumd_outputs.py",
        "--software",
        "nep",
        "--files",
        str(table),
    )

    assert result["status"] == "warning"
    assert result["schema_version"] == HELPER_SCHEMA_VERSION
    assert result["files"][0]["software"] == "nep"
    assert result["files"][0]["parser_status"] == "partial"


def test_validate_mlp_evidence_blocks_missing_production_roles(tmp_path):
    dataset = tmp_path / "dataset.json"
    dataset.write_text("{}", encoding="utf-8")

    result = _run(
        "skills/simflow-mlp/scripts/validate_mlp_evidence.py",
        "--production-readiness",
        "--evidence",
        f"dataset_manifest={dataset}",
    )

    assert result["status"] == "blocked"
    assert result["schema_version"] == HELPER_SCHEMA_VERSION
    assert result["helper"] == "validate_mlp_evidence"
    assert result["scientific_readiness"] == "blocked"
    assert "approval_record" not in result["missing_roles"]
    assert "anomaly_report" in result["missing_roles"]
    assert result["blocked_claims"] == ["production MLP-MD readiness"]


def test_validate_mlp_evidence_requires_approval_only_when_requested(tmp_path):
    paths = {}
    for role in [
        "dataset_manifest",
        "labeling_manifest",
        "training_run_manifest",
        "model_validation_report",
        "smoke_md_manifest",
        "anomaly_report",
    ]:
        path = tmp_path / f"{role}.json"
        path.write_text("{}", encoding="utf-8")
        paths[role] = path

    args = [
        "skills/simflow-mlp/scripts/validate_mlp_evidence.py",
        "--production-readiness",
    ]
    for role, path in paths.items():
        args.extend(["--evidence", f"{role}={path}"])

    ready = _run(*args)
    with_approval = _run(*args, "--require-approval")

    assert ready["status"] == "success"
    assert ready["scientific_readiness"] == "ready"
    assert ready["approval_required"] is False
    assert with_approval["status"] == "blocked"
    assert with_approval["scientific_readiness"] == "blocked"
    assert with_approval["approval_required"] is True
    assert "approval_record" in with_approval["missing_roles"]


def test_build_mlp_dataset_manifest_counts_extxyz_frames(tmp_path):
    dataset = tmp_path / "train.xyz"
    output = tmp_path / "dataset_manifest.json"
    dataset.write_text("2\nframe0\nSi 0 0 0\nSi 1 1 1\n1\nframe1\nSi 0 0 0\n", encoding="utf-8")

    result = _run(
        "skills/simflow-mlp/scripts/build_mlp_dataset_manifest.py",
        "--dataset",
        str(dataset),
        "--split",
        "train",
        "--output",
        str(output),
    )

    assert result["status"] == "success"
    assert result["schema_version"] == HELPER_SCHEMA_VERSION
    assert result["helper"] == "build_mlp_dataset_manifest"
    assert result["parser_status"] == "parsed"
    assert result["datasets"][0]["structure_count"] == 2
    assert output.is_file()


def test_summarize_mlp_metrics_uses_metrics_summary_role_and_fallback_parser(tmp_path):
    metrics = tmp_path / "metrics.tsv"
    metrics.write_text("force_rmse\tenergy_rmse\n0.1\t0.2\n", encoding="utf-8")

    result = _run(
        "skills/simflow-mlp/scripts/summarize_mlp_metrics.py",
        "--metrics",
        str(metrics),
    )

    assert result["status"] == "success"
    assert result["schema_version"] == HELPER_SCHEMA_VERSION
    assert result["helper"] == "summarize_mlp_metrics"
    assert result["parser_status"] == "parsed"
    assert result["evidence_role"] == "model_metrics_summary"
    assert result["metric_files"][0]["metrics"]["force_rmse"] == 0.1


def test_build_mlp_dataset_manifest_warns_on_malformed_extxyz(tmp_path):
    dataset = tmp_path / "train.xyz"
    output = tmp_path / "dataset_manifest.json"
    dataset.write_text("2\nframe0\nSi 0 0 0\n", encoding="utf-8")

    result = _run(
        "skills/simflow-mlp/scripts/build_mlp_dataset_manifest.py",
        "--dataset",
        str(dataset),
        "--split",
        "train",
        "--output",
        str(output),
    )

    assert result["status"] == "warning"
    assert result["schema_version"] == HELPER_SCHEMA_VERSION
    assert result["parser_status"] == "partial"
    assert result["datasets"][0]["structure_count"] is None
    assert any(warning["code"] == "structure_count_unavailable" for warning in result["warnings"])
