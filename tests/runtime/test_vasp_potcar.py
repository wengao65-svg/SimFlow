#!/usr/bin/env python3
"""Tests for runtime/lib/vasp_potcar.py"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "runtime"))

from lib.vasp_potcar import (
    read_poscar_species,
    generate_potcar,
    validate_potcar,
    _extract_potcar_elements,
    _find_element_potcar,
    _list_available_elements,
    get_potcar_path,
    get_potcar_flavor,
)


class TestReadPoscarSpecies:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.tmpdir)

    def _write_poscar(self, species_line: str, atom_counts: str) -> str:
        """Write a minimal VASP5 POSCAR."""
        poscar = os.path.join(self.tmpdir, "POSCAR")
        content = f"""Test POSCAR
1.0
  5.0 0.0 0.0
  0.0 5.0 0.0
  0.0 0.0 5.0
{species_line}
{atom_counts}
direct
  0.0 0.0 0.0
  0.5 0.5 0.5
"""
        with open(poscar, "w") as f:
            f.write(content)
        return poscar

    def test_single_element(self):
        poscar = self._write_poscar("Si", "2")
        assert read_poscar_species(poscar) == ["Si"]

    def test_multiple_elements(self):
        poscar = self._write_poscar("Si Ge O", "2 2 4")
        assert read_poscar_species(poscar) == ["Si", "Ge", "O"]

    def test_vasp4_format_raises(self):
        poscar = os.path.join(self.tmpdir, "POSCAR")
        with open(poscar, "w") as f:
            f.write("Test\n1.0\n  5 0 0\n  0 5 0\n  0 0 5\n2 2\n4\ndirect\n  0 0 0\n")
        import pytest
        with pytest.raises(ValueError, match="VASP4"):
            read_poscar_species(poscar)

    def test_file_not_found(self):
        import pytest
        with pytest.raises(FileNotFoundError):
            read_poscar_species("/nonexistent/POSCAR")

    def test_too_short_file(self):
        poscar = os.path.join(self.tmpdir, "POSCAR")
        with open(poscar, "w") as f:
            f.write("line1\nline2\n")
        import pytest
        with pytest.raises(ValueError, match="too short"):
            read_poscar_species(poscar)


class TestExtractPotcarElements:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.tmpdir)

    def _write_potcar(self, *headers) -> str:
        """Write a POTCAR with given PAW headers."""
        potcar = os.path.join(self.tmpdir, "POTCAR")
        with open(potcar, "w") as f:
            for h in headers:
                f.write(f"{h}\n")
                f.write("  1.00000000000000\n")
                f.write(" parameters from PSCTR\n")
        return potcar

    def test_single_element(self):
        potcar = self._write_potcar("PAW_PBE Si 05Jan2001")
        assert _extract_potcar_elements(potcar) == ["Si"]

    def test_multiple_elements(self):
        potcar = self._write_potcar("PAW_PBE Si 05Jan2001", "PAW_PBE Ge 07Sep2000")
        assert _extract_potcar_elements(potcar) == ["Si", "Ge"]

    def test_lda_functional(self):
        potcar = self._write_potcar("PAW Si 05Jan2001")
        assert _extract_potcar_elements(potcar) == ["Si"]


class TestFindElementPotcar:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.tmpdir)

    def _create_library(self, flavor: str, elements: dict):
        """Create a fake POTCAR library. elements = {name: content}."""
        for name, content in elements.items():
            d = os.path.join(self.tmpdir, flavor, name)
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, "POTCAR"), "w") as f:
                f.write(content)

    def test_exact_match(self):
        self._create_library("PBE", {"Si": "PAW_PBE Si\n"})
        result = _find_element_potcar(self.tmpdir, "PBE", "Si")
        assert result is not None
        assert result.name == "POTCAR"
        assert "Si" in str(result)

    def test_wildcard_match(self):
        self._create_library("PBE", {"Si_pv": "PAW_PBE Si_pv\n"})
        result = _find_element_potcar(self.tmpdir, "PBE", "Si")
        assert result is not None
        assert "Si_pv" in str(result)

    def test_no_match(self):
        self._create_library("PBE", {"Ge": "PAW_PBE Ge\n"})
        result = _find_element_potcar(self.tmpdir, "PBE", "Si")
        assert result is None

    def test_no_flavor_dir(self):
        result = _find_element_potcar(self.tmpdir, "LDA", "Si")
        assert result is None


class TestGeneratePotcar:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.tmpdir)

    def _write_poscar(self, species: str, counts: str) -> str:
        poscar = os.path.join(self.tmpdir, "POSCAR")
        with open(poscar, "w") as f:
            f.write(f"Test\n1.0\n  5 0 0\n  0 5 0\n  0 0 5\n{species}\n{counts}\ndirect\n  0 0 0\n")
        return poscar

    def _create_library(self, elements: dict):
        for name, content in elements.items():
            d = os.path.join(self.tmpdir, "potlib", "PBE", name)
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, "POTCAR"), "w") as f:
                f.write(content)

    def test_concat_single_element(self):
        poscar = self._write_poscar("Si", "2")
        self._create_library({"Si": "PAW_PBE Si 05Jan2001\n"})
        output = os.path.join(self.tmpdir, "POTCAR")
        result = generate_potcar(poscar, output, potcar_root=os.path.join(self.tmpdir, "potlib"))
        assert result["status"] == "success"
        assert result["method"] == "concatenation"
        assert result["elements"] == ["Si"]
        assert os.path.isfile(output)

    def test_concat_multi_element(self):
        poscar = self._write_poscar("Si Ge", "2 2")
        self._create_library({"Si": "PAW_PBE Si\n", "Ge": "PAW_PBE Ge\n"})
        output = os.path.join(self.tmpdir, "POTCAR")
        result = generate_potcar(poscar, output, potcar_root=os.path.join(self.tmpdir, "potlib"))
        assert result["status"] == "success"
        assert result["elements"] == ["Si", "Ge"]
        content = open(output).read()
        # Si must come before Ge
        si_pos = content.index("Si")
        ge_pos = content.index("Ge")
        assert si_pos < ge_pos

    def test_missing_element(self):
        poscar = self._write_poscar("Si Xe", "2 2")
        self._create_library({"Si": "PAW_PBE Si\n"})
        output = os.path.join(self.tmpdir, "POTCAR")
        result = generate_potcar(poscar, output, potcar_root=os.path.join(self.tmpdir, "potlib"))
        assert result["status"] == "error"
        assert "Xe" in result["message"]

    def test_no_method_available(self):
        poscar = self._write_poscar("Si", "2")
        output = os.path.join(self.tmpdir, "POTCAR")
        result = generate_potcar(poscar, output)
        assert result["status"] == "unavailable"

    def test_variant_specification(self):
        poscar = self._write_poscar("Si_pv", "2")
        self._create_library({"Si_pv": "PAW_PBE Si_pv\n", "Si": "PAW_PBE Si\n"})
        output = os.path.join(self.tmpdir, "POTCAR")
        result = generate_potcar(poscar, output, potcar_root=os.path.join(self.tmpdir, "potlib"))
        assert result["status"] == "success"
        content = open(output).read()
        assert "Si_pv" in content


class TestValidatePotcar:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.tmpdir)

    def _write_poscar(self, species: str, counts: str) -> str:
        poscar = os.path.join(self.tmpdir, "POSCAR")
        with open(poscar, "w") as f:
            f.write(f"Test\n1.0\n  5 0 0\n  0 5 0\n  0 0 5\n{species}\n{counts}\ndirect\n  0 0 0\n")
        return poscar

    def _write_potcar(self, *headers) -> str:
        potcar = os.path.join(self.tmpdir, "POTCAR")
        with open(potcar, "w") as f:
            for h in headers:
                f.write(f"{h}\n  1.0\n")
        return potcar

    def test_matching_order(self):
        poscar = self._write_poscar("Si Ge", "2 2")
        potcar = self._write_potcar("PAW_PBE Si 05Jan2001", "PAW_PBE Ge 07Sep2000")
        result = validate_potcar(poscar, potcar)
        assert result["valid"] is True

    def test_mismatched_order(self):
        poscar = self._write_poscar("Si Ge", "2 2")
        potcar = self._write_potcar("PAW_PBE Ge 07Sep2000", "PAW_PBE Si 05Jan2001")
        result = validate_potcar(poscar, potcar)
        assert result["valid"] is False
        assert "mismatch" in result["message"].lower()


class TestListAvailableElements:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.tmpdir)

    def test_lists_elements_with_potcar(self):
        for elem in ["Si", "Ge", "O"]:
            d = os.path.join(self.tmpdir, "PBE", elem)
            os.makedirs(d)
            with open(os.path.join(d, "POTCAR"), "w") as f:
                f.write("dummy")
        result = _list_available_elements(self.tmpdir, "PBE")
        assert result == ["Ge", "O", "Si"]

    def test_empty_flavor_dir(self):
        os.makedirs(os.path.join(self.tmpdir, "PBE"))
        result = _list_available_elements(self.tmpdir, "PBE")
        assert result == []

    def test_no_flavor_dir(self):
        result = _list_available_elements(self.tmpdir, "LDA")
        assert result == []


class TestEnvVars:
    def test_get_potcar_path_unset(self):
        old = os.environ.pop("SIMFLOW_VASP_POTCAR_PATH", None)
        try:
            assert get_potcar_path() is None
        finally:
            if old:
                os.environ["SIMFLOW_VASP_POTCAR_PATH"] = old

    def test_get_potcar_path_set(self):
        os.environ["SIMFLOW_VASP_POTCAR_PATH"] = "/tmp/test"
        try:
            assert get_potcar_path() == "/tmp/test"
        finally:
            del os.environ["SIMFLOW_VASP_POTCAR_PATH"]

    def test_get_potcar_flavor_default(self):
        old = os.environ.pop("SIMFLOW_VASP_POTCAR_FLAVOR", None)
        try:
            assert get_potcar_flavor() == "PBE"
        finally:
            if old:
                os.environ["SIMFLOW_VASP_POTCAR_FLAVOR"] = old

    def test_get_potcar_flavor_set(self):
        os.environ["SIMFLOW_VASP_POTCAR_FLAVOR"] = "LDA"
        try:
            assert get_potcar_flavor() == "LDA"
        finally:
            del os.environ["SIMFLOW_VASP_POTCAR_FLAVOR"]
