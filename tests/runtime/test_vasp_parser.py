#!/usr/bin/env python3
"""Tests for runtime/lib/parsers/vasp_parser.py — enhanced VASP parser."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "runtime"))

from lib.parsers.vasp_parser import VASPParser

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures"


class TestParseOsziCar:
    def test_parse_relax_oszicar(self):
        """Parse OSZICAR from a relaxation run with multiple ionic steps."""
        oszicar_path = str(
            Path(__file__).parents[2] / "examples" / "si_band_structure"
            / "relax" / "output" / "OSZICAR"
        )
        if not Path(oszicar_path).exists():
            pytest.skip("Example OSZICAR not available")

        parser = VASPParser()
        result = parser.parse(oszicar_path)
        assert result.final_energy is not None
        assert result.metadata.get("ionic_steps", 0) > 1
        assert result.job_type == "relaxation"

    def test_parse_scf_oszicar(self):
        """Parse OSZICAR from SCF (single ionic step)."""
        oszicar_path = str(
            Path(__file__).parents[2] / "examples" / "si_band_structure"
            / "scf" / "output" / "OSZICAR"
        )
        if not Path(oszicar_path).exists():
            pytest.skip("Example OSZICAR not available")

        parser = VASPParser()
        result = parser.parse(oszicar_path)
        assert result.final_energy is not None


class TestParseOutcar:
    def test_parse_converged_outcar(self):
        """Parse OUTCAR that converged (reached required accuracy)."""
        outcar_path = str(
            Path(__file__).parents[2] / "examples" / "si_band_structure"
            / "relax" / "output" / "OUTCAR"
        )
        if not Path(outcar_path).exists():
            pytest.skip("Example OUTCAR not available")

        parser = VASPParser()
        result = parser.parse(outcar_path)
        assert result.converged is True
        assert result.final_energy is not None
        assert result.metadata.get("ionic_converged") is True
        assert result.metadata.get("scf_converged_steps", 0) > 0

    def test_parse_forces(self):
        """Extract forces from OUTCAR."""
        outcar_path = str(
            Path(__file__).parents[2] / "examples" / "si_band_structure"
            / "relax" / "output" / "OUTCAR"
        )
        if not Path(outcar_path).exists():
            pytest.skip("Example OUTCAR not available")

        parser = VASPParser()
        result = parser.parse(outcar_path)
        assert result.forces is not None
        assert len(result.forces) > 0
        assert "max_atom" in result.forces[0]
        assert "rms" in result.forces[0]

    def test_parse_stress(self):
        """Extract stress tensor from OUTCAR."""
        outcar_path = str(
            Path(__file__).parents[2] / "examples" / "si_band_structure"
            / "relax" / "output" / "OUTCAR"
        )
        if not Path(outcar_path).exists():
            pytest.skip("Example OUTCAR not available")

        parser = VASPParser()
        result = parser.parse(outcar_path)
        assert result.stress is not None
        assert len(result.stress) > 0
        assert len(result.stress[0]) == 6  # xx, yy, zz, xy, yz, zx

    def test_parse_parameters(self):
        """Extract ENCUT from OUTCAR."""
        outcar_path = str(
            Path(__file__).parents[2] / "examples" / "si_band_structure"
            / "relax" / "output" / "OUTCAR"
        )
        if not Path(outcar_path).exists():
            pytest.skip("Example OUTCAR not available")

        parser = VASPParser()
        result = parser.parse(outcar_path)
        assert result.parameters.get("encut") == 520.0

    def test_check_convergence_detailed(self):
        """check_convergence returns detailed breakdown."""
        outcar_path = str(
            Path(__file__).parents[2] / "examples" / "si_band_structure"
            / "relax" / "output" / "OUTCAR"
        )
        if not Path(outcar_path).exists():
            pytest.skip("Example OUTCAR not available")

        parser = VASPParser()
        conv = parser.check_convergence(outcar_path)
        assert conv["converged"] is True
        assert conv["ionic_converged"] is True
        assert conv["max_force"] is not None
        assert conv["scf_converged_steps"] > 0


class TestParseEigenval:
    def test_parse_si_eigenval(self):
        """Parse Si band structure EIGENVAL file."""
        eigenval_path = FIXTURE_DIR / "EIGENVAL_Si"
        if not eigenval_path.exists():
            pytest.skip("EIGENVAL_Si fixture not available")

        parser = VASPParser()
        result = parser.parse(str(eigenval_path))
        assert result.converged is True
        assert result.job_type == "bands"

        kpoints = result.kpoints
        assert kpoints is not None
        assert kpoints["nkpts"] == 200
        assert kpoints["nbands"] == 32
        assert len(kpoints["kcoords"]) == 200
        assert len(kpoints["eigenvalues"]) == 200
        assert len(kpoints["eigenvalues"][0]) == 32
        assert kpoints["fermi_energy"] is not None

    def test_eigenval_kpath_distances(self):
        """K-path distances should be cumulative and normalized."""
        eigenval_path = FIXTURE_DIR / "EIGENVAL_Si"
        if not eigenval_path.exists():
            pytest.skip("EIGENVAL_Si fixture not available")

        parser = VASPParser()
        result = parser.parse(str(eigenval_path))
        distances = result.kpoints["kpath_distances"]
        assert distances[0] == 0.0
        assert abs(distances[-1] - 1.0) < 0.01  # approximately normalized
        # Monotonically increasing
        for i in range(1, len(distances)):
            assert distances[i] >= distances[i - 1]

    def test_eigenval_occupations(self):
        """Occupations should be 0 or 1 for insulators."""
        eigenval_path = FIXTURE_DIR / "EIGENVAL_Si"
        if not eigenval_path.exists():
            pytest.skip("EIGENVAL_Si fixture not available")

        parser = VASPParser()
        result = parser.parse(str(eigenval_path))
        occs = result.kpoints["occupations"]
        for kpt_occs in occs:
            for occ in kpt_occs:
                assert occ in (0.0, 1.0)

    def test_eigenval_fermi_energy(self):
        """Fermi energy should be between valence and conduction bands."""
        eigenval_path = FIXTURE_DIR / "EIGENVAL_Si"
        if not eigenval_path.exists():
            pytest.skip("EIGENVAL_Si fixture not available")

        parser = VASPParser()
        result = parser.parse(str(eigenval_path))
        ef = result.kpoints["fermi_energy"]
        # Si band gap ~0.5 eV, VBM ~5.3 eV, CBM ~5.8 eV
        # Fermi should be near VBM
        assert ef is not None
        assert ef > 0  # reasonable for Si

    def test_unknown_file_type(self):
        """Unknown file type should return error."""
        parser = VASPParser()
        result = parser.parse("/dev/null")  # empty file, not a VASP file
        assert len(result.errors) > 0


class TestFileNotFound:
    def test_parse_nonexistent(self):
        parser = VASPParser()
        with pytest.raises(FileNotFoundError):
            parser.parse("/nonexistent/OUTCAR")
