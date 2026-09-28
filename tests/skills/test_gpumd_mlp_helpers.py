"""Tests for generic MLP helper scripts."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

def _run(*args: str) -> dict:
    completed = subprocess.run([sys.executable, *args], cwd=ROOT, check=True, text=True, capture_output=True)
    return json.loads(completed.stdout)


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
    assert result["helper"] == "validate_mlp_evidence"
    assert result["scientific_readiness"]["status"] == "blocked"
    assert "approval_record" not in result["missing_roles"]
    assert "anomaly_report" in result["missing_roles"]
    assert "execution_gate" not in result
    assert result["blocked_claims"] == ["production MLP-MD readiness"]


def test_validate_mlp_evidence_reviews_scientific_fields_without_approval_gate(tmp_path):
    payloads = {
        "dataset_manifest": {"lineage_complete": True, "datasets": [{"path": "train.xyz", "split": "train", "present": True}]},
        "labeling_manifest": {"status": "completed", "label_source": "synthetic_dft_fixture"},
        "training_run_manifest": {"status": "completed", "model_artifact": "nep.txt"},
        "model_metrics_summary": {"status": "success", "metrics": {"force_rmse": 0.05}},
        "model_validation_report": {"status": "pass", "validation_domain": "synthetic_holdout", "rmse_energy_mev_atom": 5.0},
        "smoke_md_manifest": {"smoke_status": "pass", "steps": 1000},
        "anomaly_report": {"thresholds_defined": True},
        "active_learning_round_manifest": {"status": "completed", "round": "round_000"},
    }
    paths = {}
    for role, payload in payloads.items():
        path = tmp_path / f"{role}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        paths[role] = path

    args = [
        "skills/simflow-mlp/scripts/validate_mlp_evidence.py",
        "--production-readiness",
    ]
    for role, path in paths.items():
        args.extend(["--evidence", f"{role}={path}"])

    ready = _run(*args)
    assert ready["status"] == "success"
    assert ready["scientific_readiness"]["status"] == "ready"
    assert "approval_required" not in ready
    assert "execution_gate" not in ready
    assert "real_submit_allowed" not in ready


def test_validate_mlp_evidence_blocks_empty_json_even_when_roles_exist(tmp_path):
    args = [
        "skills/simflow-mlp/scripts/validate_mlp_evidence.py",
        "--production-readiness",
    ]
    for role in [
        "dataset_manifest",
        "labeling_manifest",
        "training_run_manifest",
        "model_metrics_summary",
        "model_validation_report",
        "smoke_md_manifest",
        "anomaly_report",
        "active_learning_round_manifest",
    ]:
        path = tmp_path / f"{role}.json"
        path.write_text("{}", encoding="utf-8")
        args.extend(["--evidence", f"{role}={path}"])

    result = _run(*args)

    assert result["status"] == "blocked"
    assert result["scientific_readiness"]["status"] == "blocked"
    assert result["missing_scientific_roles"] == []
    assert "dataset_manifest" in result["semantic_blocked_roles"]
    assert any(issue["code"] == "empty_evidence_json" for issue in result["semantic_issues"])
    assert result["blocked_claims"] == ["production MLP-MD readiness"]


def test_validate_mlp_evidence_blocks_directory_evidence_paths(tmp_path):
    args = [
        "skills/simflow-mlp/scripts/validate_mlp_evidence.py",
        "--production-readiness",
    ]
    for role in [
        "dataset_manifest",
        "labeling_manifest",
        "training_run_manifest",
        "model_metrics_summary",
        "model_validation_report",
        "smoke_md_manifest",
        "anomaly_report",
        "active_learning_round_manifest",
    ]:
        directory = tmp_path / role
        directory.mkdir()
        args.extend(["--evidence", f"{role}={directory}"])

    result = _run(*args)

    assert result["status"] == "blocked"
    assert result["scientific_readiness"]["status"] == "blocked"
    assert result["evidence_payload_roles"] == []
    assert {item["role"] for item in result["missing_paths"]} == {
        "dataset_manifest",
        "labeling_manifest",
        "training_run_manifest",
        "model_metrics_summary",
        "model_validation_report",
        "smoke_md_manifest",
        "anomaly_report",
        "active_learning_round_manifest",
    }
    assert any(warning["code"] == "non_file_evidence_path" for warning in result["warnings"])


def test_validate_mlp_evidence_requires_active_learning_round_for_production(tmp_path):
    payloads = {
        "dataset_manifest": {"lineage_complete": True, "datasets": [{"path": "train.xyz", "split": "train", "present": True}]},
        "labeling_manifest": {"status": "completed", "label_source": "synthetic_dft_fixture"},
        "training_run_manifest": {"status": "completed", "model_artifact": "nep.txt"},
        "model_metrics_summary": {"status": "success", "metrics": {"force_rmse": 0.05}},
        "model_validation_report": {"status": "pass", "validation_domain": "synthetic_holdout", "rmse_energy_mev_atom": 5.0},
        "smoke_md_manifest": {"smoke_status": "pass", "steps": 1000},
        "anomaly_report": {"thresholds_defined": True},
    }
    args = [
        "skills/simflow-mlp/scripts/validate_mlp_evidence.py",
        "--production-readiness",
    ]
    for role, payload in payloads.items():
        path = tmp_path / f"{role}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        args.extend(["--evidence", f"{role}={path}"])

    result = _run(*args)

    assert result["status"] == "blocked"
    assert result["scientific_readiness"]["status"] == "blocked"
    assert "active_learning_round_manifest" in result["missing_scientific_roles"]
    assert result["blocked_claims"] == ["production MLP-MD readiness"]


def test_validate_mlp_evidence_accepts_explicit_no_active_learning_decision(tmp_path):
    payloads = {
        "dataset_manifest": {"lineage_complete": True, "datasets": [{"path": "train.xyz", "split": "train", "present": True}]},
        "labeling_manifest": {"status": "completed", "label_source": "synthetic_dft_fixture"},
        "training_run_manifest": {"status": "completed", "model_artifact": "nep.txt"},
        "model_metrics_summary": {"status": "success", "metrics": {"force_rmse": 0.05}},
        "model_validation_report": {"status": "pass", "validation_domain": "synthetic_holdout", "rmse_energy_mev_atom": 5.0},
        "smoke_md_manifest": {"smoke_status": "pass", "steps": 1000},
        "anomaly_report": {"thresholds_defined": True},
        "active_learning_round_manifest": {
            "status": "completed",
            "active_learning_used": False,
            "decision_rationale": "The target domain is covered by a curated reference dataset and direct validation.",
            "residual_risk": "Rare configurations outside the validated domain may remain unsupported.",
        },
    }
    args = [
        "skills/simflow-mlp/scripts/validate_mlp_evidence.py",
        "--production-readiness",
    ]
    for role, payload in payloads.items():
        path = tmp_path / f"{role}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        args.extend(["--evidence", f"{role}={path}"])

    result = _run(*args)

    assert result["status"] == "success"
    assert result["scientific_readiness"]["status"] == "ready"
    assert result["semantic_issues"] == []


def test_validate_mlp_evidence_rejects_non_text_no_active_learning_decision(tmp_path):
    payloads = {
        "dataset_manifest": {"lineage_complete": True, "datasets": [{"path": "train.xyz", "split": "train", "present": True}]},
        "labeling_manifest": {"status": "completed", "label_source": "synthetic_dft_fixture"},
        "training_run_manifest": {"status": "completed", "model_artifact": "nep.txt"},
        "model_metrics_summary": {"status": "success", "metrics": {"force_rmse": 0.05}},
        "model_validation_report": {"status": "pass", "validation_domain": "synthetic_holdout", "rmse_energy_mev_atom": 5.0},
        "smoke_md_manifest": {"smoke_status": "pass", "steps": 1000},
        "anomaly_report": {"thresholds_defined": True},
        "active_learning_round_manifest": {
            "status": "completed",
            "active_learning_used": False,
            "decision_rationale": False,
            "residual_risk": False,
        },
    }
    args = [
        "skills/simflow-mlp/scripts/validate_mlp_evidence.py",
        "--production-readiness",
    ]
    for role, payload in payloads.items():
        path = tmp_path / f"{role}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        args.extend(["--evidence", f"{role}={path}"])

    result = _run(*args)

    assert result["status"] == "blocked"
    assert result["scientific_readiness"]["status"] == "blocked"
    assert {issue["code"] for issue in result["semantic_issues"]} >= {
        "missing_active_learning_decision_rationale",
        "missing_active_learning_residual_risk",
    }


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
        "--label-source",
        "synthetic_dft_fixture",
        "--output",
        str(output),
    )

    assert result["status"] == "success"
    assert result["helper"] == "build_mlp_dataset_manifest"
    assert result["parser_status"] == "parsed"
    assert result["lineage_complete"] is True
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
        "--label-source",
        "synthetic_dft_fixture",
        "--output",
        str(output),
    )

    assert result["status"] == "warning"
    assert result["parser_status"] == "partial"
    assert result["datasets"][0]["structure_count"] is None
    assert any(warning["code"] == "structure_count_unavailable" for warning in result["warnings"])


def test_build_mlp_dataset_manifest_partial_when_one_dataset_missing(tmp_path):
    dataset = tmp_path / "train.xyz"
    missing = tmp_path / "test.xyz"
    output = tmp_path / "dataset_manifest.json"
    dataset.write_text("1\nframe0\nSi 0 0 0\n", encoding="utf-8")

    result = _run(
        "skills/simflow-mlp/scripts/build_mlp_dataset_manifest.py",
        "--dataset",
        str(dataset),
        "--dataset",
        str(missing),
        "--split",
        "train",
        "--split",
        "test",
        "--label-source",
        "synthetic_dft_fixture",
        "--output",
        str(output),
    )

    assert result["status"] == "warning"
    assert result["parser_status"] == "partial"
    assert result["lineage_complete"] is False
    assert any(warning["code"] == "missing_dataset" for warning in result["warnings"])


def test_prepare_mlp_handoff_writes_plain_user_metadata(tmp_path):
    evidence_path = tmp_path / "dataset_manifest.json"
    output = tmp_path / "handoff.json"
    evidence_path.write_text("{}", encoding="utf-8")

    result = _run(
        "skills/simflow-mlp/scripts/prepare_mlp_handoff.py",
        "--evidence",
        f"dataset_manifest={evidence_path}",
        "--output",
        str(output),
        "--goal",
        "review MLP evidence",
    )

    assert result["status"] == "success"
    assert result["helper"] == "prepare_mlp_handoff"
    assert result["evidence_role"] == "mlp_handoff"
    assert result["parser_status"] == "parsed"
    assert "production MLP-MD readiness" in result["blocked_claims"]
    assert "model_metrics_summary" in result["missing_production_roles"]
