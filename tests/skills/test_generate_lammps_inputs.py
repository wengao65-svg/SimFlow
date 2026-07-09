#!/usr/bin/env python3
"""Tests for the LAMMPS input helper."""

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "skills" / "simflow-lammps" / "scripts" / "generate_lammps_inputs.py"
POSCAR = ROOT / "tests" / "fixtures" / "POSCAR_Si"


def _load_module():
    spec = importlib.util.spec_from_file_location("simflow_lammps_inputs_test", str(SCRIPT_PATH))
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_generate_input_script_uses_configured_atom_style():
    mod = _load_module()
    with tempfile.TemporaryDirectory() as tmpdir:
        output = Path(tmpdir) / "in.lammps"

        mod.generate_input_script(
            "nvt",
            "data.lammps",
            "lj/cut",
            "* * 1.0 1.0",
            str(output),
            {"atom_style": "charge"},
        )

        text = output.read_text(encoding="utf-8")
        assert "atom_style      charge" in text
        assert "fix             1 all nvt" in text


def test_generate_lammps_inputs_writes_traceable_manifest():
    mod = _load_module()
    with tempfile.TemporaryDirectory() as tmpdir:
        result = mod.generate_lammps_inputs(
            str(POSCAR),
            "minimize",
            tmpdir,
            pair_style="tersoff",
            pair_coeff="* * Si.tersoff Si",
            params={
                "force_field_source": "user-provided Si.tersoff path",
                "potential_files": ["Si.tersoff"],
            },
        )
        manifest_path = Path(tmpdir) / "lammps_input_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        assert result["status"] == "success"
        assert (Path(tmpdir) / "in.lammps").is_file()
        assert (Path(tmpdir) / "data.lammps").is_file()
        assert manifest["software"] == "lammps"
        assert manifest["job_type"] == "minimize"
        assert manifest["pair_style"] == "tersoff"
        assert manifest["force_field_provenance"]["redistributed_by_simflow"] is False
        assert manifest["force_field_provenance"]["potential_files"] == ["Si.tersoff"]
        assert manifest["warnings"] == []


def test_generate_lammps_inputs_returns_clarification_for_unknown_job():
    mod = _load_module()
    with tempfile.TemporaryDirectory() as tmpdir:
        result = mod.generate_lammps_inputs(str(POSCAR), "viscosity", tmpdir)

        assert result["status"] == "needs_clarification"
        assert "viscosity" in result["message"]
        assert result["supported_job_types"] == ["minimize", "npt", "nve", "nvt"]
        assert "use inspect_lammps_inputs.py for static evidence checks" in result["candidate_paths"]
        assert "force-field provenance" in result["missing_information"]


def test_generate_lammps_inputs_requires_explicit_mlp_deployment_inputs():
    mod = _load_module()
    with tempfile.TemporaryDirectory() as tmpdir:
        result = mod.generate_lammps_inputs(
            str(POSCAR),
            "mlp_md",
            tmpdir,
            pair_style="pace",
            pair_coeff="* * model.yace Si",
            params={"force_field_source": "synthetic PACE fixture"},
        )

        assert result["status"] == "needs_inputs"
        assert result["job_type"] == "mlp_md"
        assert result["handoff_to"] == "simflow-mlp"
        assert "model_files" in result["missing_information"]
        assert "type_mapping" in result["missing_information"]
        assert "lammps_package_evidence" in result["missing_information"]
        assert result["claim_limits"] == [
            "MLP-MD scaffold generation records LAMMPS deployment needs only.",
            "It does not validate model training quality, extrapolation safety, or production readiness.",
        ]


def test_generate_lammps_inputs_cli_accepts_mlp_md_for_needs_inputs():
    with tempfile.TemporaryDirectory() as tmpdir:
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "--input",
                str(POSCAR),
                "--job-type",
                "mlp_md",
                "--pair-style",
                "pace",
                "--pair-coeff",
                "* * model.yace Si",
                "--output-dir",
                tmpdir,
                "--params",
                json.dumps({"force_field_source": "synthetic PACE fixture"}),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )

        assert completed.returncode == 0
        result = json.loads(completed.stdout)
        assert result["status"] == "needs_inputs"
        assert result["job_type"] == "mlp_md"
