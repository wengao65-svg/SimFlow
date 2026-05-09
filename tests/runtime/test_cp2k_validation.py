#!/usr/bin/env python3
"""Tests for CP2K validation helpers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "runtime"))

from lib.cp2k_input import generate_input, write_xyz
from lib.cp2k_validation import validate_cp2k_inputs


def _write_valid_energy_case(tmp_path: Path) -> Path:
    coord = tmp_path / "structure.xyz"
    coord.write_text(
        write_xyz(
            3,
            "water",
            [
                "O 0.0 0.0 0.0",
                "H 0.7 0.5 0.0",
                "H -0.7 0.5 0.0",
            ],
        ),
        encoding="utf-8",
    )
    inp = tmp_path / "energy.inp"
    inp.write_text(
        generate_input(
            {
                "coord_file": "structure.xyz",
                "coord_path": str(coord),
                "elements": ["O", "H"],
            },
            "energy",
        ),
        encoding="utf-8",
    )
    return inp


def _checks_by_name(report: dict) -> dict:
    return {item["check"]: item for item in report["checks"]}


def test_missing_global_run_type(tmp_path):
    inp = _write_valid_energy_case(tmp_path)
    inp.write_text(inp.read_text().replace("  RUN_TYPE ENERGY\n", ""), encoding="utf-8")
    report = validate_cp2k_inputs("energy", str(tmp_path), input_path=str(inp))
    assert report["status"] == "fail"
    assert _checks_by_name(report)["global_run_type"]["passed"] is False


def test_missing_force_eval_dft(tmp_path):
    inp = _write_valid_energy_case(tmp_path)
    content = inp.read_text(encoding="utf-8")
    start = content.index("&FORCE_EVAL")
    end = content.index("&SUBSYS")
    inp.write_text(content[:start] + "&FORCE_EVAL\n  METHOD QS\n&END FORCE_EVAL\n", encoding="utf-8")
    report = validate_cp2k_inputs("energy", str(tmp_path), input_path=str(inp))
    assert _checks_by_name(report)["force_eval_dft"]["passed"] is False


def test_missing_basis_and_potential_file_names(tmp_path):
    inp = _write_valid_energy_case(tmp_path)
    text = inp.read_text(encoding="utf-8")
    text = text.replace("    BASIS_SET_FILE_NAME BASIS_MOLOPT\n", "")
    text = text.replace("    POTENTIAL_FILE_NAME POTENTIAL\n", "")
    inp.write_text(text, encoding="utf-8")
    report = validate_cp2k_inputs("energy", str(tmp_path), input_path=str(inp))
    checks = _checks_by_name(report)
    assert checks["basis_set_file_name"]["passed"] is False
    assert checks["potential_file_name"]["passed"] is False


def test_missing_mgrid_scf_ot_xc(tmp_path):
    inp = _write_valid_energy_case(tmp_path)
    text = inp.read_text(encoding="utf-8")
    for marker in (
        """    &MGRID
      CUTOFF 400
      REL_CUTOFF 50
    &END MGRID
""",
        """    &SCF
      MAX_SCF 50
      EPS_SCF 1e-06
      SCF_GUESS ATOMIC
      &OT ON
        MINIMIZER DIIS
        PRECONDITIONER FULL_SINGLE_INVERSE
      &END OT
      &OUTER_SCF
        MAX_SCF 20
        EPS_SCF 1e-06
      &END OUTER_SCF
      &PRINT
        &RESTART OFF
        &END RESTART
      &END PRINT
    &END SCF
""",
        """    &XC
      &XC_FUNCTIONAL PBE
      &END XC_FUNCTIONAL
    &END XC
""",
    ):
        text = text.replace(marker, "")
    inp.write_text(text, encoding="utf-8")
    report = validate_cp2k_inputs("energy", str(tmp_path), input_path=str(inp))
    checks = _checks_by_name(report)
    assert checks["mgrid"]["passed"] is False
    assert checks["scf"]["passed"] is False
    assert checks["ot"]["passed"] is False
    assert checks["xc"]["passed"] is False


def test_missing_coord_file(tmp_path):
    inp = _write_valid_energy_case(tmp_path)
    (tmp_path / "structure.xyz").unlink()
    report = validate_cp2k_inputs("energy", str(tmp_path), input_path=str(inp))
    assert _checks_by_name(report)["coord_file_exists"]["passed"] is False


def test_kind_not_covering_all_elements(tmp_path):
    coord = tmp_path / "structure.xyz"
    coord.write_text(
        write_xyz(
            3,
            "co",
            [
                "C 0.0 0.0 0.0",
                "O 1.0 0.0 0.0",
                "H 0.0 1.0 0.0",
            ],
        ),
        encoding="utf-8",
    )
    inp = tmp_path / "energy.inp"
    inp.write_text(
        generate_input(
            {
                "coord_file": "structure.xyz",
                "coord_path": str(coord),
                "elements": ["O", "H"],
            },
            "energy",
        ),
        encoding="utf-8",
    )
    report = validate_cp2k_inputs("energy", str(tmp_path), input_path=str(inp))
    assert _checks_by_name(report)["kind_coverage"]["passed"] is False


def test_run_type_motion_mismatch(tmp_path):
    coord = tmp_path / "structure.xyz"
    coord.write_text(
        write_xyz(2, "si", ["Si 0 0 0", "Si 1 1 1"]),
        encoding="utf-8",
    )
    inp = tmp_path / "bad.inp"
    inp.write_text(
        generate_input(
            {
                "coord_file": "structure.xyz",
                "coord_path": str(coord),
                "elements": ["Si"],
            },
            "aimd_nvt",
        ).replace("RUN_TYPE MD", "RUN_TYPE ENERGY"),
        encoding="utf-8",
    )
    report = validate_cp2k_inputs("aimd_nvt", str(tmp_path), input_path=str(inp))
    assert _checks_by_name(report)["run_type_motion_match"]["passed"] is False


def test_missing_restart_file(tmp_path):
    coord = tmp_path / "structure.xyz"
    coord.write_text(write_xyz(2, "si", ["Si 0 0 0", "Si 1 1 1"]), encoding="utf-8")
    inp = tmp_path / "restart.inp"
    inp.write_text(
        generate_input(
            {
                "coord_file": "structure.xyz",
                "coord_path": str(coord),
                "elements": ["Si"],
                "restart_file": "missing.restart",
            },
            "aimd_nvt",
        ),
        encoding="utf-8",
    )
    report = validate_cp2k_inputs("restart", str(tmp_path), input_path=str(inp))
    assert _checks_by_name(report)["restart_file_exists"]["passed"] is False
