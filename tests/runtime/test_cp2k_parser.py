#!/usr/bin/env python3
"""Tests for runtime/lib/parsers/cp2k_parser.py."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "runtime"))

from lib.parsers.cp2k_parser import CP2KParser

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures"


class TestParseLog:
    def test_parse_converged(self):
        """Parse converged CP2K .log file."""
        log_path = FIXTURE_DIR / "CP2K_H2O.log"
        if not log_path.exists():
            pytest.skip("CP2K_H2O.log fixture not available")

        parser = CP2KParser()
        result = parser.parse(str(log_path))
        assert result.converged is True
        assert result.software == "cp2k"
        assert result.job_type == "md"
        assert result.final_energy is not None

    def test_parse_final_energy(self):
        """Final energy is the last ENERGY line."""
        log_path = FIXTURE_DIR / "CP2K_H2O.log"
        if not log_path.exists():
            pytest.skip("CP2K_H2O.log fixture not available")

        parser = CP2KParser()
        result = parser.parse(str(log_path))
        assert result.final_energy is not None
        assert abs(result.final_energy - (-34.123448)) < 0.001

    def test_parse_scf_converged_steps(self):
        """SCF convergence count is extracted."""
        log_path = FIXTURE_DIR / "CP2K_H2O.log"
        if not log_path.exists():
            pytest.skip("CP2K_H2O.log fixture not available")

        parser = CP2KParser()
        result = parser.parse(str(log_path))
        assert result.metadata.get("scf_converged_steps", 0) > 0

    def test_parse_md_steps(self):
        """MD step count is extracted."""
        log_path = FIXTURE_DIR / "CP2K_H2O.log"
        if not log_path.exists():
            pytest.skip("CP2K_H2O.log fixture not available")

        parser = CP2KParser()
        result = parser.parse(str(log_path))
        assert result.metadata.get("md_steps", 0) > 0

    def test_parse_not_converged(self):
        """Parse a file that didn't converge."""
        import tempfile
        content = """ CP2K| version string: CP2K version 2026.1
 GLOBAL| Run type  ENERGY
 ABORT: Something went wrong
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            f.write(content)
            f.flush()
            parser = CP2KParser()
            result = parser.parse(f.name)
            assert result.converged is False
            assert len(result.errors) > 0

    def test_check_convergence(self):
        """check_convergence returns detailed breakdown."""
        log_path = FIXTURE_DIR / "CP2K_H2O.log"
        if not log_path.exists():
            pytest.skip("CP2K_H2O.log fixture not available")

        parser = CP2KParser()
        conv = parser.check_convergence(str(log_path))
        assert conv["converged"] is True
        assert conv["final_energy"] is not None
        assert conv["job_type"] == "md"


class TestParseEner:
    def test_parse_ener(self):
        """Parse .ener file and extract per-step data."""
        ener_path = FIXTURE_DIR / "CP2K_H2O-1.ener"
        if not ener_path.exists():
            pytest.skip("CP2K_H2O-1.ener fixture not available")

        parser = CP2KParser()
        data = parser.parse_ener(str(ener_path))
        assert len(data["steps"]) == 3
        assert data["steps"] == [1, 2, 3]
        assert len(data["temperature"]) == 3
        assert abs(data["temperature"][0] - 300.0) < 0.1
        assert len(data["potential"]) == 3
        assert len(data["times"]) == 3

    def test_parse_ener_values(self):
        """Energy values are reasonable."""
        ener_path = FIXTURE_DIR / "CP2K_H2O-1.ener"
        if not ener_path.exists():
            pytest.skip("CP2K_H2O-1.ener fixture not available")

        parser = CP2KParser()
        data = parser.parse_ener(str(ener_path))
        for temp in data["temperature"]:
            assert 200 < temp < 400  # reasonable temperature range
        for pot in data["potential"]:
            assert pot < 0  # negative potential energy


class TestParseTrajectory:
    def test_parse_trajectory(self):
        """Parse trajectory XYZ and extract frames."""
        traj_path = FIXTURE_DIR / "CP2K_H2O-pos-1.xyz"
        if not traj_path.exists():
            pytest.skip("Trajectory fixture not available")

        parser = CP2KParser()
        frames = parser.parse_trajectory(str(traj_path))
        assert len(frames) == 4
        assert frames[0]["natoms"] == 6
        assert frames[0]["step"] == 0
        assert frames[-1]["step"] == 3

    def test_parse_trajectory_atoms(self):
        """Atom data is correctly parsed."""
        traj_path = FIXTURE_DIR / "CP2K_H2O-pos-1.xyz"
        if not traj_path.exists():
            pytest.skip("Trajectory fixture not available")

        parser = CP2KParser()
        frames = parser.parse_trajectory(str(traj_path))
        atoms = frames[0]["atoms"]
        assert len(atoms) == 6
        assert atoms[0]["element"] == "O"
        assert atoms[1]["element"] == "H"

    def test_parse_trajectory_times(self):
        """Frame times are correctly extracted."""
        traj_path = FIXTURE_DIR / "CP2K_H2O-pos-1.xyz"
        if not traj_path.exists():
            pytest.skip("Trajectory fixture not available")

        parser = CP2KParser()
        frames = parser.parse_trajectory(str(traj_path))
        assert frames[0]["time"] == 0.0
        assert frames[1]["time"] == 0.5
        assert frames[2]["time"] == 1.0
        assert frames[3]["time"] == 1.5

    def test_parse_trajectory_energy(self):
        """Frame energies are extracted."""
        traj_path = FIXTURE_DIR / "CP2K_H2O-pos-1.xyz"
        if not traj_path.exists():
            pytest.skip("Trajectory fixture not available")

        parser = CP2KParser()
        frames = parser.parse_trajectory(str(traj_path))
        for frame in frames:
            assert frame["energy"] is not None
            assert frame["energy"] < 0  # negative total energy


class TestParseTrajectoryExtxyz:
    def test_parse_extxyz_frames(self):
        """Parse EXTXYZ trajectory and extract frames."""
        traj_path = FIXTURE_DIR / "CP2K_EXTXYZ-pos-1.xyz"
        if not traj_path.exists():
            pytest.skip("EXTXYZ fixture not available")

        parser = CP2KParser()
        frames = parser.parse_trajectory(str(traj_path))
        assert len(frames) == 2
        assert frames[0]["natoms"] == 422
        assert frames[0]["step"] == 0
        assert frames[1]["step"] == 200

    def test_parse_extxyz_metadata(self):
        """EXTXYZ step/time/energy are correctly extracted."""
        traj_path = FIXTURE_DIR / "CP2K_EXTXYZ-pos-1.xyz"
        if not traj_path.exists():
            pytest.skip("EXTXYZ fixture not available")

        parser = CP2KParser()
        frames = parser.parse_trajectory(str(traj_path))
        assert frames[0]["time"] == 0.0
        assert frames[1]["time"] == 100.0
        assert frames[0]["energy"] is not None
        assert frames[0]["energy"] < 0
        assert frames[1]["energy"] is not None

    def test_parse_extxyz_atoms(self):
        """EXTXYZ atom data is correctly parsed."""
        traj_path = FIXTURE_DIR / "CP2K_EXTXYZ-pos-1.xyz"
        if not traj_path.exists():
            pytest.skip("EXTXYZ fixture not available")

        parser = CP2KParser()
        frames = parser.parse_trajectory(str(traj_path))
        atoms = frames[0]["atoms"]
        assert len(atoms) == 422
        # First atom is Si
        assert atoms[0]["element"] == "Si"
        # Check coordinates are floats
        assert isinstance(atoms[0]["x"], float)


class TestFileNotFound:
    def test_parse_nonexistent(self):
        parser = CP2KParser()
        with pytest.raises(FileNotFoundError):
            parser.parse("/nonexistent/file.log")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
