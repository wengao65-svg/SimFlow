#!/usr/bin/env python3
"""Tests for the LAMMPS static inspection helper."""

from __future__ import annotations

import importlib.util
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
