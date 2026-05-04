#!/usr/bin/env python3
"""Tests for runtime/lib/cp2k_input.py."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "runtime"))

from lib.cp2k_input import (
    cp2k_defaults,
    extract_last_frame,
    generate_input,
    read_cif_to_xyz,
    write_xyz,
)

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures"
H2O_CIF = Path(__file__).resolve().parents[2] / "examples" / "h2o" / "H2O.cif"


class TestCpkDefaults:
    def test_aimd_nvt_defaults(self):
        """AIMD NVT defaults contain required keys."""
        d = cp2k_defaults("aimd_nvt")
        assert d["steps"] == 200
        assert d["timestep"] == 0.5
        assert d["temperature"] == 300.0
        assert d["thermostat_type"] == "CSVR"
        assert d["cutoff"] == 400
        assert d["xc_functional"] == "PBE"

    def test_energy_defaults(self):
        """Energy defaults contain required keys."""
        d = cp2k_defaults("energy")
        assert "cutoff" in d
        assert "xc_functional" in d
        assert "coord_file" in d

    def test_unknown_calc_type_raises(self):
        """Unknown calc type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown calc_type"):
            cp2k_defaults("invalid")


class TestGenerateInput:
    def test_generate_aimd_nvt_defaults(self):
        """AIMD NVT input with defaults contains key sections."""
        inp = generate_input({}, "aimd_nvt")
        assert "&GLOBAL" in inp
        assert "RUN_TYPE MD" in inp
        assert "ENSEMBLE NVT" in inp
        assert "STEPS 200" in inp
        assert "TIMESTEP 0.5" in inp
        assert "TEMPERATURE 300.0" in inp
        assert "TYPE CSVR" in inp
        assert "CUTOFF 400" in inp
        assert "XC_FUNCTIONAL PBE" in inp
        assert "DZVP-MOLOPT-SR-GTH" in inp
        assert "GTH-PBE-q6" in inp
        assert "GTH-PBE-q1" in inp

    def test_generate_aimd_nvt_custom(self):
        """AIMD NVT input with custom parameters."""
        inp = generate_input(
            {"temperature": 500, "steps": 100, "cutoff": 500},
            "aimd_nvt",
        )
        assert "TEMPERATURE 500" in inp
        assert "STEPS 100" in inp
        assert "CUTOFF 500" in inp

    def test_generate_energy_input(self):
        """Energy input has RUN_TYPE ENERGY and no MD section."""
        inp = generate_input({}, "energy")
        assert "RUN_TYPE ENERGY" in inp
        assert "&MOTION" not in inp
        assert "ENSEMBLE" not in inp
        assert "CUTOFF 400" in inp

    def test_generate_energy_custom(self):
        """Energy input with custom parameters."""
        inp = generate_input({"cutoff": 600, "max_scf": 100}, "energy")
        assert "CUTOFF 600" in inp
        assert "MAX_SCF 100" in inp

    def test_unknown_calc_type_raises(self):
        """Unknown calc type raises ValueError."""
        with pytest.raises(ValueError):
            generate_input({}, "invalid")


class TestMultiElementKind:
    def test_single_element_kind(self):
        """Single element KIND block (O only)."""
        inp = generate_input(
            {"elements": ["O"], "element_params": {"O": {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q6"}}},
            "energy",
        )
        assert "&KIND O" in inp
        assert "BASIS_SET DZVP-MOLOPT-SR-GTH" in inp
        assert "POTENTIAL GTH-PBE-q6" in inp
        assert "&KIND H" not in inp

    def test_multi_element_kind(self):
        """Multiple elements generate sorted KIND blocks."""
        inp = generate_input(
            {
                "elements": ["H", "O", "Si"],
                "element_params": {
                    "H": {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q1"},
                    "O": {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q6"},
                    "Si": {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q4"},
                },
            },
            "energy",
        )
        assert "&KIND H" in inp
        assert "&KIND O" in inp
        assert "&KIND Si" in inp
        # KIND blocks appear in sorted order
        h_pos = inp.index("&KIND H")
        o_pos = inp.index("&KIND O")
        si_pos = inp.index("&KIND Si")
        assert h_pos < o_pos < si_pos

    def test_elements_use_default_params(self):
        """Elements without explicit element_params use DEFAULT_ELEMENT_PARAMS."""
        inp = generate_input({"elements": ["O", "H"]}, "energy")
        assert "POTENTIAL GTH-PBE-q6" in inp
        assert "POTENTIAL GTH-PBE-q1" in inp

    def test_elements_override_default_params(self):
        """element_params override DEFAULT_ELEMENT_PARAMS."""
        inp = generate_input(
            {
                "elements": ["O"],
                "element_params": {"O": {"basis": "TZV2P-MOLOPT-GTH", "potential": "GTH-PBE-q6"}},
            },
            "energy",
        )
        assert "TZV2P-MOLOPT-GTH" in inp

    def test_unknown_element_raises(self):
        """Unknown element without params raises ValueError."""
        with pytest.raises(ValueError, match="No basis/potential"):
            generate_input({"elements": ["Xx"]}, "energy")

    def test_legacy_mode_without_elements(self):
        """Without elements key, uses legacy O/H hardcoded KIND."""
        inp = generate_input({}, "energy")
        assert "&KIND O" in inp
        assert "&KIND H" in inp
        assert "GTH-PBE-q6" in inp
        assert "GTH-PBE-q1" in inp

    def test_aimd_nvt_multi_element(self):
        """AIMD NVT also supports multi-element KIND."""
        inp = generate_input(
            {
                "elements": ["Si", "O", "H"],
                "element_params": {
                    "Si": {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q4"},
                    "O": {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q6"},
                    "H": {"basis": "DZVP-MOLOPT-SR-GTH", "potential": "GTH-PBE-q1"},
                },
            },
            "aimd_nvt",
        )
        assert "&KIND H" in inp
        assert "&KIND O" in inp
        assert "&KIND Si" in inp
        assert "RUN_TYPE MD" in inp


class TestTrajFormat:
    def test_default_traj_format_xyz(self):
        """Default trajectory format is XYZ."""
        inp = generate_input({}, "aimd_nvt")
        assert "FORMAT XYZ" in inp

    def test_traj_format_extxyz(self):
        """EXTXYZ trajectory format option."""
        inp = generate_input({"traj_format": "EXTXYZ"}, "aimd_nvt")
        assert "FORMAT EXTXYZ" in inp

    def test_traj_format_not_in_energy(self):
        """Energy input has no trajectory section."""
        inp = generate_input({}, "energy")
        assert "&TRAJECTORY" not in inp
        assert "&MOTION" not in inp


class TestCoordFormat:
    def test_default_coord_format_xyz(self):
        """Default coordinate format is XYZ."""
        inp = generate_input({}, "aimd_nvt")
        assert "COORD_FILE_FORMAT XYZ" in inp

    def test_coord_format_cif(self):
        """CIF coordinate format option."""
        inp = generate_input({"coord_format": "CIF", "coord_file": "structure.cif"}, "aimd_nvt")
        assert "COORD_FILE_FORMAT CIF" in inp
        assert "COORD_FILE_NAME structure.cif" in inp


class TestReadCifToXyz:
    @pytest.mark.skipif(not H2O_CIF.exists(), reason="H2O.cif not available")
    def test_read_h2o_cif(self):
        """Read H2O.cif and extract cell + atoms."""
        cell_abc, xyz_lines, element_counts = read_cif_to_xyz(str(H2O_CIF))
        assert len(cell_abc.split()) == 3
        assert len(xyz_lines) > 0
        assert "O" in element_counts
        assert "H" in element_counts
        assert element_counts["O"] > 0
        assert element_counts["H"] > 0

    @pytest.mark.skipif(not H2O_CIF.exists(), reason="H2O.cif not available")
    def test_xyz_line_format(self):
        """XYZ lines have correct format."""
        _, xyz_lines, _ = read_cif_to_xyz(str(H2O_CIF))
        for line in xyz_lines:
            parts = line.split()
            assert len(parts) == 4  # element x y z
            assert parts[0] in ("O", "H")
            # x, y, z should be floats
            float(parts[1])
            float(parts[2])
            float(parts[3])

    @pytest.mark.skipif(not H2O_CIF.exists(), reason="H2O.cif not available")
    def test_cell_parameters(self):
        """Cell parameters match CIF file."""
        cell_abc, _, _ = read_cif_to_xyz(str(H2O_CIF))
        parts = cell_abc.split()
        # H2O.cif has a=b=c=15.494660
        assert abs(float(parts[0]) - 15.49466) < 0.001

    def test_nonexistent_file_raises(self):
        """Nonexistent CIF file raises error."""
        with pytest.raises(FileNotFoundError):
            read_cif_to_xyz("/nonexistent/file.cif")


class TestWriteXyz:
    def test_write_xyz_format(self):
        """write_xyz produces correct XYZ format."""
        lines = ["O  1.0  2.0  3.0", "H  4.0  5.0  6.0"]
        xyz = write_xyz(2, "test comment", lines)
        assert xyz.startswith("2\n")
        assert "test comment" in xyz
        assert "O  1.0  2.0  3.0" in xyz


class TestExtractLastFrame:
    def test_extract_from_multi_frame(self):
        """Extract last frame from multi-frame trajectory."""
        trajectory = """6
i = 0, time = 0.0
O  1.0  2.0  3.0
H  4.0  5.0  6.0
H  7.0  8.0  9.0
O  10.0  11.0  12.0
H  13.0  14.0  15.0
H  16.0  17.0  18.0
6
i = 1, time = 0.5
O  1.1  2.1  3.1
H  4.1  5.1  6.1
H  7.1  8.1  9.1
O  10.1  11.1  12.1
H  13.1  14.1  15.1
H  16.1  17.1  18.1
"""
        last = extract_last_frame(trajectory)
        assert "i = 1" in last
        assert "1.1" in last
        assert last.startswith("6\n")

    def test_extract_single_frame(self):
        """Extract from single-frame trajectory."""
        trajectory = """3
i = 0, time = 0.0
O  1.0  2.0  3.0
H  4.0  5.0  6.0
H  7.0  8.0  9.0
"""
        last = extract_last_frame(trajectory)
        assert "i = 0" in last
        assert "O" in last

    def test_empty_trajectory_raises(self):
        """Empty trajectory raises ValueError."""
        with pytest.raises(ValueError, match="No frames"):
            extract_last_frame("")

    @pytest.mark.skipif(
        not (FIXTURE_DIR / "CP2K_H2O-pos-1.xyz").exists(),
        reason="Trajectory fixture not available",
    )
    def test_extract_from_fixture(self):
        """Extract last frame from fixture trajectory."""
        content = (FIXTURE_DIR / "CP2K_H2O-pos-1.xyz").read_text()
        last = extract_last_frame(content)
        assert "i =       3" in last
        assert last.startswith("6\n")

    def test_extract_from_extxyz(self):
        """Extract last frame from EXTXYZ-format trajectory."""
        trajectory = """4
Lattice="10.0 0.0 0.0 0.0 10.0 0.0 0.0 0.0 10.0" Properties="species:S:1:pos:R:3" Step=0 Time=0.000 Energy=-100.0
Si  0.0  0.0  0.0
O   1.0  1.0  1.0
H   2.0  2.0  2.0
H   3.0  3.0  3.0
4
Lattice="10.0 0.0 0.0 0.0 10.0 0.0 0.0 0.0 10.0" Properties="species:S:1:pos:R:3" Step=200 Time=100.000 Energy=-100.5
Si  0.1  0.1  0.1
O   1.1  1.1  1.1
H   2.1  2.1  2.1
H   3.1  3.1  3.1
"""
        last = extract_last_frame(trajectory)
        assert "Step=200" in last
        assert "0.1" in last
        assert last.startswith("4\n")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
