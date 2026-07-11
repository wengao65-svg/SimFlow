"""Tests for GPUMD/NEP and generic MLP helper scripts."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


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


def _has_nested_key_value(value: object, key: str, expected: object) -> bool:
    if isinstance(value, dict):
        return any(
            (item_key == key and item_value == expected)
            or _has_nested_key_value(item_value, key, expected)
            for item_key, item_value in value.items()
        )
    if isinstance(value, list):
        return any(_has_nested_key_value(item, key, expected) for item in value)
    return False


def _has_scientific_readiness_pass(value: object) -> bool:
    if isinstance(value, dict):
        for item_key, item_value in value.items():
            if item_key == "scientific_readiness":
                if item_value == "pass":
                    return True
                if isinstance(item_value, dict) and item_value.get("status") == "pass":
                    return True
            if _has_scientific_readiness_pass(item_value):
                return True
    if isinstance(value, list):
        return any(_has_scientific_readiness_pass(item) for item in value)
    return False


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
    assert result["tool_capabilities"]["gpumd"]["tool_support_level"] == "helper_supported"
    assert any(warning["code"] == "missing_expected_file" for warning in result["warnings"])
    assert any(warning["code"] == "missing_referenced_file" for warning in result["warnings"])


def test_build_gpumd_manifest_records_helper_supported_tool_support(tmp_path):
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
    assert result["actual_tool_used"]["support_level"] == "helper_supported"
    assert result["tool_support"]["builtin_helpers"] == ["gpumd", "nep"]
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


def test_generate_and_validate_gpumd_inputs_from_structure_and_existing_potential(tmp_path):
    structure = ROOT / "tests" / "fixtures" / "Si.cif"
    potential = tmp_path / "nep.txt"
    potential.write_text("dummy potential fixture\n", encoding="utf-8")

    generated = _run(
        "skills/simflow-gpumd/scripts/generate_gpumd_inputs.py",
        "--structure",
        str(structure),
        "--task",
        "nvt",
        "--project-root",
        str(tmp_path),
        "--calc-dir",
        "calc",
        "--params",
        '{"potential_file": "nep.txt", "steps": 10}',
    )
    validated = _run(
        "skills/simflow-gpumd/scripts/validate_gpumd_inputs.py",
        "--task",
        "nvt",
        "--calc-dir",
        str(tmp_path / "calc"),
    )

    assert generated["status"] == "success"
    assert generated["actual_tool_used"]["support_level"] == "helper_supported"
    assert (tmp_path / "calc" / "run.in").is_file()
    assert (tmp_path / "calc" / "model.xyz").is_file()
    assert validated["status"] == "pass"
    assert not _has_scientific_readiness_pass(validated)
    assert {check["check"] for check in validated["checks"]} >= {"run_in_exists", "model_xyz_exists", "potential_command"}


def test_generate_gpumd_inputs_needs_existing_potential(tmp_path):
    structure = ROOT / "tests" / "fixtures" / "Si.cif"

    result = _run(
        "skills/simflow-gpumd/scripts/generate_gpumd_inputs.py",
        "--structure",
        str(structure),
        "--task",
        "nvt",
        "--project-root",
        str(tmp_path),
        "--calc-dir",
        "calc",
    )

    assert result["status"] == "needs_inputs"
    assert result["missing_inputs"] == ["potential_file"]
    assert result["simflow_result"]["role"] == "helper"
    assert result["simflow_result"]["activity"] == "input_generation"
    assert result["simflow_result"]["stage"] == "computation"
    assert result["simflow_result"]["state_effect"] == "none"


def test_generate_gpumd_inputs_recording_preserves_helper_authored_simflow_result(tmp_path):
    structure = ROOT / "tests" / "fixtures" / "Si.cif"
    potential = tmp_path / "nep.txt"
    potential.write_text("dummy potential fixture\n", encoding="utf-8")

    result = _run(
        "skills/simflow-gpumd/scripts/generate_gpumd_inputs.py",
        "--structure",
        str(structure),
        "--task",
        "nvt",
        "--project-root",
        str(tmp_path),
        "--calc-dir",
        "calc",
        "--params",
        '{"potential_file": "nep.txt", "steps": 10}',
        "--record-helper-run",
    )

    assert result["status"] == "success"
    assert result["simflow_result"]["role"] == "helper"
    assert result["simflow_result"]["activity"] == "input_generation"
    assert result["simflow_result"]["stage"] == "computation"
    assert result["simflow_result"]["state_effect"] == "record_only"


def test_generate_nep_inputs_from_existing_dataset(tmp_path):
    train = tmp_path / "train.xyz"
    train.write_text(
        '1\nlattice="5 0 0 0 5 0 0 0 5" energy=-1 properties=species:S:1:pos:R:3:force:R:3\nSi 0 0 0 0 0 0\n',
        encoding="utf-8",
    )

    result = _run(
        "skills/simflow-gpumd/scripts/generate_gpumd_inputs.py",
        "--task",
        "nep_training",
        "--software",
        "nep",
        "--project-root",
        str(tmp_path),
        "--calc-dir",
        "nep_calc",
        "--params",
        '{"train_xyz": "train.xyz", "generation": 100}',
    )

    assert result["status"] == "success"
    assert result["software"] == "nep"
    assert result["actual_tool_used"]["support_level"] == "helper_supported"
    assert (tmp_path / "nep_calc" / "nep.in").is_file()
    assert (tmp_path / "nep_calc" / "train.xyz").is_file()


def test_generate_nep_inputs_needs_existing_train_xyz(tmp_path):
    result = _run(
        "skills/simflow-gpumd/scripts/generate_gpumd_inputs.py",
        "--task",
        "nep_training",
        "--software",
        "nep",
        "--project-root",
        str(tmp_path),
        "--calc-dir",
        "nep_calc",
    )

    assert result["status"] == "needs_inputs"
    assert result["task"] == "nep_training"
    assert result["missing_inputs"] == ["train_xyz"]


def test_orchestrate_gpumd_task_writes_reports_and_checkpoint(tmp_path):
    structure = ROOT / "tests" / "fixtures" / "Si.cif"
    potential = tmp_path / "nep.txt"
    potential.write_text("dummy potential fixture\n", encoding="utf-8")
    _run(
        "skills/simflow-gpumd/scripts/generate_gpumd_inputs.py",
        "--structure",
        str(structure),
        "--task",
        "nvt",
        "--project-root",
        str(tmp_path),
        "--calc-dir",
        "calc",
        "--params",
        '{"potential_file": "nep.txt", "steps": 10}',
    )

    result = _run(
        "skills/simflow-gpumd/scripts/orchestrate_gpumd_task.py",
        "--task",
        "nvt",
        "--project-root",
        str(tmp_path),
        "--calc-dir",
        "calc",
    )

    assert result["status"] == "success"
    assert result["simflow_result"]["role"] == "helper"
    assert result["simflow_result"]["activity"] == "orchestration"
    assert result["simflow_result"]["stage"] == "computation"
    assert result["simflow_result"]["state_effect"] == "none"
    assert (tmp_path / "reports" / "gpumd" / "input_manifest.json").is_file()
    assert (tmp_path / "reports" / "gpumd" / "validation_report.json").is_file()
    compute_plan = json.loads((tmp_path / "reports" / "gpumd" / "compute_plan.json").read_text(encoding="utf-8"))
    assert compute_plan["task"] == "gpumd_md_nvt"
    assert compute_plan["real_submit_allowed"] is False
    assert "checkpoint" not in result
    assert "artifacts" not in result
    assert not (tmp_path / ".simflow").exists()


def test_orchestrate_unknown_gpumd_task_does_not_fallback_to_nvt_or_training(tmp_path):
    result = _run(
        "skills/simflow-gpumd/scripts/orchestrate_gpumd_task.py",
        "--task",
        "made_up_task",
        "--project-root",
        str(tmp_path),
        "--calc-dir",
        "calc",
    )

    manifest = json.loads((tmp_path / "reports" / "gpumd" / "input_manifest.json").read_text(encoding="utf-8"))
    validation = json.loads((tmp_path / "reports" / "gpumd" / "validation_report.json").read_text(encoding="utf-8"))
    compute_plan = json.loads((tmp_path / "reports" / "gpumd" / "compute_plan.json").read_text(encoding="utf-8"))

    assert result["status"] == "needs_clarification"
    assert result["task"] == "unknown"
    assert manifest["task"] == "unknown"
    assert manifest["classification_status"] == "needs_clarification"
    assert validation["status"] == "skip"
    assert compute_plan["task"] == "unknown"
    assert compute_plan["real_submit_allowed"] is False
    assert compute_plan["task"] not in {"gpumd_md_nvt", "nep_training"}
    assert result["simflow_result"]["state_effect"] == "none"
    assert "checkpoint" not in result
    assert not (tmp_path / ".simflow").exists()


def test_orchestrate_gpumd_warning_keeps_computation_in_progress(tmp_path):
    calc = tmp_path / "calc"
    calc.mkdir()
    (calc / "run.in").write_text(
        "potential nep.txt\ntime_step 1\nensemble nvt_ber 300 300 100\nrun 10\n",
        encoding="utf-8",
    )
    (calc / "model.xyz").write_text(
        '1\npbc="T T T" lattice="5 0 0 0 5 0 0 0 5" properties=species:S:1:pos:R:3\nSi 0 0 0\nBAD_TRAILING_LINE\n',
        encoding="utf-8",
    )
    (calc / "nep.txt").write_text("fixture\n", encoding="utf-8")

    result = _run(
        "skills/simflow-gpumd/scripts/orchestrate_gpumd_task.py",
        "--task",
        "nvt",
        "--project-root",
        str(tmp_path),
        "--calc-dir",
        "calc",
    )
    assert result["status"] == "warning"
    assert result["simflow_result"]["state_effect"] == "none"
    assert "checkpoint" not in result
    assert not (tmp_path / ".simflow").exists()


def test_orchestrate_gpumd_record_helper_run_creates_helper_artifacts_only(tmp_path):
    structure = ROOT / "tests" / "fixtures" / "Si.cif"
    potential = tmp_path / "nep.txt"
    potential.write_text("dummy potential fixture\n", encoding="utf-8")
    _run(
        "skills/simflow-gpumd/scripts/generate_gpumd_inputs.py",
        "--structure",
        str(structure),
        "--task",
        "nvt",
        "--project-root",
        str(tmp_path),
        "--calc-dir",
        "calc",
        "--params",
        '{"potential_file": "nep.txt", "steps": 10}',
    )

    result = _run(
        "skills/simflow-gpumd/scripts/orchestrate_gpumd_task.py",
        "--task",
        "nvt",
        "--project-root",
        str(tmp_path),
        "--calc-dir",
        "calc",
        "--record-helper-run",
    )

    assert result["status"] == "success"
    assert result["simflow_result"]["state_effect"] == "record_only"
    checkpoints = json.loads((tmp_path / ".simflow/state/checkpoints.json").read_text(encoding="utf-8"))
    stages = json.loads((tmp_path / ".simflow/state/stages.json").read_text(encoding="utf-8"))
    artifacts = json.loads((tmp_path / ".simflow/state/artifacts.json").read_text(encoding="utf-8"))
    manifest_path = next(
        tmp_path / artifact["path"]
        for artifact in artifacts
        if artifact["type"] == "helper_run_manifest"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert checkpoints == []
    assert stages == {}
    assert manifest["metadata"]["simflow_result"]["state_effect"] == "record_only"
    assert {artifact["type"] for artifact in artifacts} == {
        "helper_script",
        "helper_output",
        "helper_run_manifest",
    }


@pytest.mark.parametrize("calc_dir_factory", [lambda root: "../outside", lambda root: str(root.parent / "outside-abs")])
def test_gpumd_scripts_reject_calc_dir_outside_project_root(tmp_path, calc_dir_factory):
    structure = ROOT / "tests" / "fixtures" / "Si.cif"
    outside = tmp_path.parent / "outside-abs"

    generate = subprocess.run(
        [
            sys.executable,
            "skills/simflow-gpumd/scripts/generate_gpumd_inputs.py",
            "--structure",
            str(structure),
            "--task",
            "nvt",
            "--project-root",
            str(tmp_path),
            "--calc-dir",
            calc_dir_factory(tmp_path),
            "--params",
            '{"potential_file": "nep.txt"}',
        ],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    orchestrate = subprocess.run(
        [
            sys.executable,
            "skills/simflow-gpumd/scripts/orchestrate_gpumd_task.py",
            "--task",
            "nvt",
            "--project-root",
            str(tmp_path),
            "--calc-dir",
            calc_dir_factory(tmp_path),
        ],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )

    assert generate.returncode == 1
    assert orchestrate.returncode == 1
    assert "project" in generate.stdout.lower() or "boundary" in generate.stdout.lower()
    assert "project" in orchestrate.stdout.lower() or "boundary" in orchestrate.stdout.lower()
    assert not outside.exists()
    assert not (tmp_path.parent / "outside").exists()


def test_orchestrate_gpumd_failed_validation_blocks_stage(tmp_path):
    result = _run(
        "skills/simflow-gpumd/scripts/orchestrate_gpumd_task.py",
        "--task",
        "nvt",
        "--project-root",
        str(tmp_path),
        "--calc-dir",
        "calc",
    )

    assert result["status"] == "blocked"
    assert result["stage_status"] == "failed"
    assert result["checkpoint_status"] == "failure"
    assert result["simflow_result"]["state_effect"] == "none"
    assert not (tmp_path / ".simflow").exists()


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
    assert not _has_nested_key_value(result, "production_ready", True)
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


def test_parse_gpumd_outputs_recognizes_nep_train_test_tables(tmp_path):
    energy = tmp_path / "energy_train.out"
    force = tmp_path / "force_test.out"
    energy.write_text("0 0.1\n1 0.05\n", encoding="utf-8")
    force.write_text("0 0.2 0.3\n1 0.1 0.15\n", encoding="utf-8")

    result = _run(
        "skills/simflow-gpumd/scripts/parse_gpumd_outputs.py",
        "--files",
        str(energy),
        str(force),
    )

    roles = {item["role"] for item in result["files"]}
    assert result["status"] == "success"
    assert result["parser_status"] == "parsed"
    assert result["actual_tool_used"]["software"] == "nep"
    assert roles == {"nep_energy_train_table", "nep_force_test_table"}
    assert "model-quality" in result["claim_limits"][0]


def test_parse_gpumd_outputs_marks_malformed_existing_table_blocked(tmp_path):
    malformed = tmp_path / "stress_test.out"
    malformed.write_text("not numeric\nstill not numeric\n", encoding="utf-8")

    result = _run(
        "skills/simflow-gpumd/scripts/parse_gpumd_outputs.py",
        "--files",
        str(malformed),
    )

    parsed = result["files"][0]
    assert result["status"] == "blocked"
    assert result["parser_status"] == "malformed"
    assert parsed["role"] == "nep_stress_test_table"
    assert parsed["parser_status"] == "malformed"
    assert any(warning["code"] == "no_numeric_rows" for warning in parsed["warnings"])


def test_parse_gpumd_outputs_warns_on_mixed_gpumd_nep_files(tmp_path):
    thermo = tmp_path / "thermo.out"
    loss = tmp_path / "loss.out"
    thermo.write_text("0 300 1.0\n", encoding="utf-8")
    loss.write_text("step loss\n0 0.5\n", encoding="utf-8")

    result = _run(
        "skills/simflow-gpumd/scripts/parse_gpumd_outputs.py",
        "--files",
        str(thermo),
        str(loss),
    )

    statuses = {item["parser_status"] for item in result["files"]}
    assert result["status"] == "warning"
    assert result["parser_status"] == "partial"
    assert result["actual_tool_used"]["software"] == "gpumd"
    assert statuses == {"parsed", "partial"}


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
    assert result["scientific_readiness"]["status"] == "blocked"
    assert "approval_record" not in result["missing_roles"]
    assert "anomaly_report" in result["missing_roles"]
    assert result["execution_gate"]["status"] == "not_requested"
    assert result["blocked_claims"] == ["production MLP-MD readiness", "real production MLP-MD execution"]


def test_validate_mlp_evidence_requires_approval_only_when_requested(tmp_path):
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
    with_approval = _run(*args, "--require-approval")
    approval_record = tmp_path / "approval_record.json"
    approval_record.write_text("{}", encoding="utf-8")
    approved = _run(
        *args,
        "--require-approval",
        "--evidence",
        f"approval_record={approval_record}",
    )

    assert ready["status"] == "success"
    assert ready["scientific_readiness"]["status"] == "ready"
    assert ready["approval_required"] is False
    assert ready["execution_gate"]["status"] == "not_requested"
    assert ready["production_md_gate_approved"] is False
    assert ready["real_submit_gate"]["gate"] == "hpc_submit"
    assert ready["real_submit_allowed"] is False
    assert with_approval["status"] == "warning"
    assert with_approval["scientific_readiness"]["status"] == "ready"
    assert with_approval["approval_required"] is True
    assert with_approval["execution_gate"]["status"] == "approval_required"
    assert with_approval["execution_gate"]["gate_scope"] == "production_md_readiness_only"
    assert with_approval["execution_gate"]["production_md_gate_approved"] is False
    assert with_approval["real_submit_allowed"] is False
    assert "approval_record" in with_approval["missing_execution_roles"]
    assert "approval_record" in with_approval["missing_roles"]
    assert with_approval["blocked_claims"] == ["real production MLP-MD execution"]
    assert approved["status"] == "success"
    assert approved["scientific_readiness"]["status"] == "ready"
    assert approved["approval_required"] is True
    assert approved["execution_gate"]["status"] == "approved"
    assert approved["execution_gate"]["production_md_gate_approved"] is True
    assert approved["production_md_gate_approved"] is True
    assert approved["execution_gate"]["real_submit_allowed"] is False
    assert approved["real_submit_allowed"] is False
    assert approved["real_submit_gate"]["status"] == "required_for_real_submit"
    assert approved["blocked_claims"] == ["real production MLP-MD execution"]


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
    assert result["blocked_claims"] == ["production MLP-MD readiness", "real production MLP-MD execution"]


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
    assert result["blocked_claims"] == ["production MLP-MD readiness", "real production MLP-MD execution"]


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
    assert result["schema_version"] == HELPER_SCHEMA_VERSION
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
        "--label-source",
        "synthetic_dft_fixture",
        "--output",
        str(output),
    )

    assert result["status"] == "warning"
    assert result["schema_version"] == HELPER_SCHEMA_VERSION
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


def test_prepare_mlp_handoff_uses_helper_evidence_envelope(tmp_path):
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
    assert result["schema_version"] == HELPER_SCHEMA_VERSION
    assert result["helper"] == "prepare_mlp_handoff"
    assert result["evidence_role"] == "mlp_handoff"
    assert result["parser_status"] == "parsed"
    assert "production MLP-MD readiness" in result["blocked_claims"]
    assert "model_metrics_summary" in result["missing_production_roles"]


def test_prepare_gpumd_handoff_uses_helper_evidence_envelope(tmp_path):
    manifest = tmp_path / "manifest.json"
    output = tmp_path / "handoff.json"
    manifest.write_text('{"status": "success"}\n', encoding="utf-8")

    result = _run(
        "skills/simflow-gpumd/scripts/prepare_gpumd_handoff.py",
        "--manifest",
        str(manifest),
        "--output",
        str(output),
    )

    assert result["status"] == "success"
    assert result["schema_version"] == HELPER_SCHEMA_VERSION
    assert result["helper"] == "prepare_gpumd_handoff"
    assert result["capability"] == "evidence_handoff"
    assert result["stage"] == "writing"
    assert result["activity"] == "gpumd_nep_evidence_handoff"
    assert result["evidence_role"] == "gpumd_nep_handoff"
    assert result["source_files"][0]["sha256"]
    assert result["actual_tool_used"]["support_level"] == "helper_supported"
    assert result["parser_status"] == "parsed"
    assert result["claim_limits"]
    assert result["limitations"]
    assert result["parent_artifacts"] == []
    assert output.is_file()


def test_prepare_gpumd_handoff_preserves_degraded_source_status(tmp_path):
    manifest = tmp_path / "manifest.json"
    output = tmp_path / "handoff.json"
    manifest.write_text(
        '{"status": "incomplete", "parser_status": "malformed"}\n',
        encoding="utf-8",
    )

    result = _run(
        "skills/simflow-gpumd/scripts/prepare_gpumd_handoff.py",
        "--manifest",
        str(manifest),
        "--output",
        str(output),
    )

    assert result["status"] == "warning"
    assert result["parser_status"] == "partial"
    assert {warning["code"] for warning in result["warnings"]} >= {
        "degraded_source_status",
        "degraded_parser_status",
    }
