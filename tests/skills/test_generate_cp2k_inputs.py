#!/usr/bin/env python3
"""Tests for generate_cp2k_inputs.py skill script."""

import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures"
SCRIPT_PATH = Path(__file__).resolve().parents[2] / "skills" / "simflow-input-generation" / "scripts" / "generate_cp2k_inputs.py"
H2O_CIF = Path(__file__).resolve().parents[2] / "examples" / "h2o" / "H2O.cif"


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.skipif(not H2O_CIF.exists(), reason="H2O.cif not available")
class TestGenerateAimdNvt:
    def test_generates_inp(self):
        """AIMD NVT generates .inp file."""
        mod = _load_module("cp2k_gen", SCRIPT_PATH)
        with tempfile.TemporaryDirectory() as tmpdir:
            result = mod.generate_cp2k_inputs(str(H2O_CIF), "aimd_nvt", tmpdir)
            assert result["status"] == "success"
            assert os.path.exists(os.path.join(tmpdir, "aimd_nvt.inp"))
            assert os.path.exists(os.path.join(tmpdir, "structure.xyz"))

    def test_inp_contains_nvt(self):
        """Generated input has NVT parameters."""
        mod = _load_module("cp2k_gen", SCRIPT_PATH)
        with tempfile.TemporaryDirectory() as tmpdir:
            result = mod.generate_cp2k_inputs(str(H2O_CIF), "aimd_nvt", tmpdir)
            inp = Path(os.path.join(tmpdir, "aimd_nvt.inp")).read_text()
            assert "RUN_TYPE MD" in inp
            assert "ENSEMBLE NVT" in inp
            assert "STEPS 200" in inp
            assert "TEMPERATURE 300.0" in inp
            assert "TYPE CSVR" in inp

    def test_custom_params(self):
        """Custom parameters override defaults."""
        mod = _load_module("cp2k_gen", SCRIPT_PATH)
        with tempfile.TemporaryDirectory() as tmpdir:
            result = mod.generate_cp2k_inputs(
                str(H2O_CIF), "aimd_nvt", tmpdir,
                params={"temperature": 500, "steps": 100},
            )
            inp = Path(os.path.join(tmpdir, "aimd_nvt.inp")).read_text()
            assert "TEMPERATURE 500" in inp
            assert "STEPS 100" in inp

    def test_result_metadata(self):
        """Result contains structure metadata."""
        mod = _load_module("cp2k_gen", SCRIPT_PATH)
        with tempfile.TemporaryDirectory() as tmpdir:
            result = mod.generate_cp2k_inputs(str(H2O_CIF), "aimd_nvt", tmpdir)
            assert result["parameters"]["natoms"] > 0
            assert "O" in result["parameters"]["elements"]
            assert "H" in result["parameters"]["elements"]

    def test_structure_xyz_content(self):
        """structure.xyz has correct format."""
        mod = _load_module("cp2k_gen", SCRIPT_PATH)
        with tempfile.TemporaryDirectory() as tmpdir:
            mod.generate_cp2k_inputs(str(H2O_CIF), "aimd_nvt", tmpdir)
            xyz = Path(os.path.join(tmpdir, "structure.xyz")).read_text()
            lines = xyz.strip().split("\n")
            natoms = int(lines[0])
            assert natoms > 0
            assert len(lines) == natoms + 2  # natoms + comment + atoms


@pytest.mark.skipif(not H2O_CIF.exists(), reason="H2O.cif not available")
class TestGenerateEnergy:
    def test_generates_inp(self):
        """Energy generates .inp file."""
        mod = _load_module("cp2k_gen", SCRIPT_PATH)
        with tempfile.TemporaryDirectory() as tmpdir:
            result = mod.generate_cp2k_inputs(str(H2O_CIF), "energy", tmpdir)
            assert result["status"] == "success"
            assert os.path.exists(os.path.join(tmpdir, "energy.inp"))

    def test_inp_contains_energy(self):
        """Generated input has ENERGY run type."""
        mod = _load_module("cp2k_gen", SCRIPT_PATH)
        with tempfile.TemporaryDirectory() as tmpdir:
            result = mod.generate_cp2k_inputs(str(H2O_CIF), "energy", tmpdir)
            inp = Path(os.path.join(tmpdir, "energy.inp")).read_text()
            assert "RUN_TYPE ENERGY" in inp
            assert "ENSEMBLE" not in inp


@pytest.mark.skipif(not H2O_CIF.exists(), reason="H2O.cif not available")
class TestCliJsonOutput:
    def test_json_output(self):
        """Script outputs valid JSON."""
        mod = _load_module("cp2k_gen", SCRIPT_PATH)
        with tempfile.TemporaryDirectory() as tmpdir:
            result = mod.generate_cp2k_inputs(str(H2O_CIF), "aimd_nvt", tmpdir)
            # Should be serializable
            json_str = json.dumps(result)
            parsed = json.loads(json_str)
            assert parsed["status"] == "success"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
