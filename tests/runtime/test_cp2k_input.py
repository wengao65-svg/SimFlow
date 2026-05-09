#!/usr/bin/env python3
"""Tests for common-task CP2K input generation."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "runtime"))

from lib.cp2k_input import (
    cp2k_defaults,
    extract_last_frame,
    generate_input,
    read_xyz_structure,
    write_xyz,
)


def _structure_xyz() -> str:
    return write_xyz(
        3,
        "water",
        [
            "O 0.000000 0.000000 0.000000",
            "H 0.757000 0.586000 0.000000",
            "H -0.757000 0.586000 0.000000",
        ],
    )


def test_defaults_cover_supported_tasks():
    assert cp2k_defaults("energy")["coord_file"] == "last_frame.xyz"
    assert cp2k_defaults("geo_opt")["project_name"] == "cp2k_geo_opt"
    assert cp2k_defaults("cell_opt")["project_name"] == "cp2k_cell_opt"
    assert cp2k_defaults("aimd_nvt")["temperature"] == 300.0
    assert cp2k_defaults("aimd_nve")["project_name"] == "cp2k_aimd_nve"
    assert cp2k_defaults("aimd_npt")["pressure_bar"] == 1.0


@pytest.mark.parametrize(
    ("task", "run_type", "motion_text"),
    [
        ("energy", "RUN_TYPE ENERGY", None),
        ("geo_opt", "RUN_TYPE GEO_OPT", "&GEO_OPT"),
        ("cell_opt", "RUN_TYPE CELL_OPT", "&CELL_OPT"),
        ("aimd_nvt", "RUN_TYPE MD", "ENSEMBLE NVT"),
        ("aimd_nve", "RUN_TYPE MD", "ENSEMBLE NVE"),
        ("aimd_npt", "RUN_TYPE MD", "ENSEMBLE NPT_I"),
    ],
)
def test_generate_common_inputs(task, run_type, motion_text):
    inp = generate_input({"elements": ["H", "O"]}, task)
    assert "&GLOBAL" in inp
    assert run_type in inp
    assert "&FORCE_EVAL" in inp
    assert "&DFT" in inp
    assert "&MGRID" in inp
    assert "&SCF" in inp
    assert "&KIND H" in inp
    assert "&KIND O" in inp
    if motion_text is None:
        assert "&MOTION" not in inp
    else:
        assert "&MOTION" in inp
        assert motion_text in inp


def test_geo_opt_has_expected_threshold_fields():
    inp = generate_input({"elements": ["O", "H"]}, "geo_opt")
    assert "MAX_FORCE" in inp
    assert "RMS_FORCE" in inp
    assert "MAX_DR" in inp
    assert "RMS_DR" in inp


def test_cell_opt_has_pressure_and_keep_symmetry():
    inp = generate_input({"elements": ["Si"]}, "cell_opt")
    assert "EXTERNAL_PRESSURE [bar]" in inp
    assert "KEEP_SYMMETRY" in inp


def test_aimd_npt_has_thermostat_and_barostat():
    inp = generate_input({"elements": ["O", "H"]}, "aimd_npt")
    assert "&THERMOSTAT" in inp
    assert "&BAROSTAT" in inp
    assert "PRESSURE [bar]" in inp


def test_restart_input_support():
    inp = generate_input(
        {
            "elements": ["O", "H"],
            "restart_file": "md-1.restart",
        },
        "aimd_nvt",
    )
    assert "&EXT_RESTART" in inp
    assert "RESTART_FILE_NAME md-1.restart" in inp
    assert "SCF_GUESS RESTART" in inp


def test_kind_blocks_cover_all_elements_from_coord_path(tmp_path):
    coord = tmp_path / "structure.xyz"
    coord.write_text(
        write_xyz(
            4,
            "methanol fragment",
            [
                "C 0.0 0.0 0.0",
                "O 1.0 0.0 0.0",
                "H 0.0 1.0 0.0",
                "H 0.0 0.0 1.0",
            ],
        ),
        encoding="utf-8",
    )
    inp = generate_input(
        {
            "coord_path": str(coord),
            "coord_file": "structure.xyz",
        },
        "energy",
    )
    assert "&KIND C" in inp
    assert "&KIND O" in inp
    assert "&KIND H" in inp


def test_cell_abc_overrides_defaults():
    inp = generate_input(
        {
            "elements": ["O", "H"],
            "cell_abc": "10 11 12",
        },
        "energy",
    )
    assert "ABC 10 11 12" in inp


def test_write_xyz_and_read_xyz_structure_round_trip(tmp_path):
    xyz_path = tmp_path / "structure.xyz"
    xyz_path.write_text(_structure_xyz(), encoding="utf-8")
    atom_lines, counts, comment = read_xyz_structure(xyz_path)
    assert len(atom_lines) == 3
    assert counts == {"O": 1, "H": 2}
    assert comment == "water"


def test_extract_last_frame():
    trajectory = _structure_xyz() + _structure_xyz().replace("water", "water-2")
    last_frame = extract_last_frame(trajectory)
    assert "water-2" in last_frame
    assert last_frame.startswith("3\n")


def test_unknown_calc_type_raises():
    with pytest.raises(ValueError, match="Unknown calc_type"):
        cp2k_defaults("unsupported")
