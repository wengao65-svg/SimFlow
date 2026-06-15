#!/usr/bin/env python3
"""Tests for the LAMMPS static inspection helper."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "skills" / "simflow-lammps" / "scripts" / "inspect_lammps_inputs.py"
SAFE_EXAMPLE = ROOT / "examples" / "lammps_safe_dry_run" / "input" / "in.lammps"


SYNTHETIC_DATA = """LAMMPS data file - synthetic fixture

2 atoms
1 atom types

0.0 8.0 xlo xhi
0.0 8.0 ylo yhi
0.0 8.0 zlo zhi

Masses

1 39.948

Atoms # atomic

1 1 3.5 4.0 4.0
2 1 4.5 4.0 4.0
"""


def _load_module():
    spec = importlib.util.spec_from_file_location("simflow_lammps_inspect_test", str(SCRIPT_PATH))
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_input_package(tmp_path: Path, script_text: str, data_text: str = SYNTHETIC_DATA) -> Path:
    script = tmp_path / "in.lammps"
    script.write_text(script_text, encoding="utf-8")
    (tmp_path / "data.lammps").write_text(data_text, encoding="utf-8")
    return script


def test_inspect_lammps_inputs_passes_synthetic_safe_example():
    mod = _load_module()

    result = mod.inspect_lammps_inputs(str(SAFE_EXAMPLE), force_field_source="synthetic LJ fixture")

    assert result["status"] == "pass"
    assert result["helper_evidence"]["schema_version"] == "simflow.helper_evidence.v1"
    assert result["helper_evidence"]["status"] == "success"
    assert result["required_checks"] == {
        "units": True,
        "atom_style": True,
        "system_definition": True,
        "pair_style": True,
        "pair_coeff": True,
        "operation": True,
    }
    assert result["data_file"]["present"] is True
    assert result["force_field_provenance"]["redistributed_by_simflow"] is False
    assert result["lammps_mlp_deployment_manifest"]["detected"] is False
    assert "dry_run_report_before_execution" in result["recommended_artifacts"]


def test_inspect_lammps_inputs_reports_missing_data_file(tmp_path):
    mod = _load_module()
    script = tmp_path / "in.lammps"
    script.write_text(
        "\n".join([
            "units lj",
            "atom_style atomic",
            "read_data missing.data",
            "pair_style lj/cut 2.5",
            "pair_coeff 1 1 1.0 1.0 2.5",
            "minimize 1.0e-6 1.0e-8 100 1000",
        ]),
        encoding="utf-8",
    )

    result = mod.inspect_lammps_inputs(str(script))

    assert result["status"] == "error"
    assert result["missing_required_files"] == [str(tmp_path / "missing.data")]
    assert any(warning["code"] == "missing_data_file" for warning in result["warnings"])


def test_inspect_lammps_inputs_detects_analysis_motifs_and_time_origin(tmp_path):
    mod = _load_module()
    script = _write_input_package(
        tmp_path,
        "\n".join([
            "units lj",
            "atom_style atomic",
            "read_data data.lammps",
            "pair_style lj/cut 2.5",
            "pair_coeff 1 1 1.0 1.0 2.5",
            "fix 1 all nve",
            "compute msd all msd com yes",
            "fix 9 all vector 10 c_msd[4]",
            "variable fitslope equal slope(f_9)/4/(10*dt)",
            "compute gofr all rdf 100",
            "fix rdf all ave/time 100 10 1000 c_gofr[*] file rdf.dat mode vector",
            "run 1000",
        ]),
    )

    result = mod.inspect_lammps_inputs(str(script), force_field_source="synthetic LJ fixture")
    motifs = {item["motif"] for item in result["local_example_motifs"]}
    warning_codes = {item["code"] for item in result["warnings"]}

    assert result["intent_candidates"]["has_msd"] is True
    assert result["intent_candidates"]["has_rdf"] is True
    assert "rdf_adf" in motifs
    assert "msd_time_origin_review" in warning_codes


def test_inspect_lammps_inputs_records_force_field_provenance_warning(tmp_path):
    mod = _load_module()
    script = _write_input_package(
        tmp_path,
        "\n".join([
            "units metal",
            "atom_style atomic",
            "read_data data.lammps",
            "pair_style tersoff",
            "pair_coeff * * Si.tersoff Si",
            "minimize 1.0e-6 1.0e-8 100 1000",
        ]),
    )

    result = mod.inspect_lammps_inputs(str(script))

    assert result["status"] == "warning"
    assert result["force_field_provenance"]["potential_files"] == ["Si.tersoff"]
    assert result["force_field_provenance"]["potential_file_records"][0]["present"] is False
    assert any(warning["code"] == "force_field_source_not_documented" for warning in result["warnings"])


def test_inspect_lammps_inputs_flags_modular_include_scripts(tmp_path):
    mod = _load_module()
    script = _write_input_package(
        tmp_path,
        "\n".join([
            "include init.mod",
            "include potential.mod",
            "fix 3 all box/relax aniso 0.0",
            "minimize ${etol} ${ftol} ${maxiter} ${maxeval}",
        ]),
    )

    result = mod.inspect_lammps_inputs(str(script))
    motifs = {item["motif"] for item in result["local_example_motifs"]}
    warning_codes = {item["code"] for item in result["warnings"]}

    assert result["status"] == "warning"
    assert "elastic_modular" in motifs
    assert "include_files_not_expanded" in warning_codes
    assert "missing_required_input_items" in warning_codes


def test_inspect_lammps_inputs_records_mlp_deployment_model_provenance(tmp_path):
    mod = _load_module()
    model = tmp_path / "graph.pb"
    model.write_text("synthetic model bytes", encoding="utf-8")
    script = _write_input_package(
        tmp_path,
        "\n".join([
            "units metal",
            "atom_style atomic",
            "read_data data.lammps",
            "pair_style deepmd graph.pb",
            "pair_coeff * *",
            "fix 1 all nve",
            "dump traj all custom 100 dump.lammpstrj id type x y z",
            "restart 1000 restart.*.bin",
            "run 1000",
        ]),
    )

    result = mod.inspect_lammps_inputs(str(script), force_field_source="synthetic MLP fixture")
    deployment = result["lammps_mlp_deployment_manifest"]
    dump_restart = result["dump_restart_manifest"]

    assert result["status"] == "pass"
    assert deployment["detected"] is True
    assert deployment["pair_styles"] == ["deepmd"]
    assert deployment["model_files"][0]["token"] == "graph.pb"
    assert deployment["model_files"][0]["present"] is True
    assert deployment["model_files"][0]["sha256"]
    assert deployment["handoff_to"] == "simflow-mlp"
    assert "training quality" in deployment["claim_limits"][1]
    assert dump_restart["dumps"][0]["file"] == "dump.lammpstrj"
    assert dump_restart["restarts"][0]["files"] == ["restart.*.bin"]


def test_inspect_lammps_inputs_writes_mlp_deployment_handoff_json(tmp_path):
    model = tmp_path / "graph.pb"
    model.write_text("synthetic model bytes", encoding="utf-8")
    script = _write_input_package(
        tmp_path,
        "\n".join([
            "units metal",
            "atom_style atomic",
            "read_data data.lammps",
            "pair_style deepmd graph.pb",
            "pair_coeff * *",
            "fix 1 all nve",
            "run 1000",
        ]),
    )
    output = tmp_path / "lammps_mlp_deployment.json"

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--input-script",
            str(script),
            "--force-field-source",
            "synthetic MLP fixture",
            "--mlp-deployment-output",
            str(output),
        ],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    result = json.loads(completed.stdout)
    deployment = json.loads(output.read_text(encoding="utf-8"))

    assert result["mlp_deployment_output"] == str(output)
    assert deployment["schema_version"] == "simflow.helper_evidence.v1"
    assert deployment["status"] == "success"
    assert deployment["evidence_role"] == "lammps_mlp_deployment_manifest"
    assert deployment["capability"] == "mlp_deployment_manifest"
    assert deployment["actual_tool_used"]["software"] == "lammps"
    assert deployment["model_files"][0]["sha256"]
    assert deployment["handoff_to"] == "simflow-mlp"
    assert "training quality" in deployment["claim_limits"][1]


def test_inspect_lammps_inputs_writes_warning_when_mlp_deployment_not_detected(tmp_path):
    script = _write_input_package(
        tmp_path,
        "\n".join([
            "units lj",
            "atom_style atomic",
            "read_data data.lammps",
            "pair_style lj/cut 2.5",
            "pair_coeff 1 1 1.0 1.0 2.5",
            "fix 1 all nve",
            "run 1000",
        ]),
    )
    output = tmp_path / "lammps_mlp_deployment.json"

    subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--input-script",
            str(script),
            "--force-field-source",
            "synthetic LJ fixture",
            "--mlp-deployment-output",
            str(output),
        ],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    deployment = json.loads(output.read_text(encoding="utf-8"))

    assert deployment["status"] == "warning"
    assert deployment["parser_status"] == "not_applicable"
    assert deployment["detected"] is False
    assert any(warning["code"] == "mlp_deployment_not_detected" for warning in deployment["warnings"])


def test_inspect_lammps_inputs_warns_on_missing_mlp_model_file(tmp_path):
    mod = _load_module()
    script = _write_input_package(
        tmp_path,
        "\n".join([
            "units metal",
            "atom_style atomic",
            "read_data data.lammps",
            "pair_style mace no_domain_decomposition",
            "pair_coeff * * missing.model-lammps Si",
            "minimize 1.0e-6 1.0e-8 100 1000",
        ]),
    )

    result = mod.inspect_lammps_inputs(str(script))
    warning_codes = {item["code"] for item in result["warnings"]}
    deployment = result["lammps_mlp_deployment_manifest"]

    assert result["status"] == "warning"
    assert deployment["detected"] is True
    assert deployment["pair_styles"] == ["mace"]
    assert deployment["model_files"][0]["present"] is False
    assert "missing_mlp_model_file" in warning_codes
    assert "mlp_deployment_source_not_documented" in warning_codes
