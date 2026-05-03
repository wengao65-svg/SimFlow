#!/usr/bin/env python3
"""Tests for generate_vasp_inputs.py skill scripts."""

import importlib
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures"
INPUT_GEN_SCRIPT = Path(__file__).resolve().parents[2] / "skills" / "simflow-input-generation" / "scripts" / "generate_vasp_inputs.py"
VASP_SCRIPT = Path(__file__).resolve().parents[2] / "skills" / "simflow-vasp" / "scripts" / "generate_vasp_inputs.py"


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_input_gen_incar():
    mod = _load_module("input_gen", INPUT_GEN_SCRIPT)
    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, "INCAR")
        mod.generate_incar("scf", {"job_name": "test"}, out)
        content = Path(out).read_text()
        assert "SYSTEM = test" in content
        assert "NSW" in content


def test_input_gen_kpoints():
    mod = _load_module("input_gen", INPUT_GEN_SCRIPT)
    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, "KPOINTS")
        mod.generate_kpoints({"kx": 4, "ky": 4, "kz": 4}, out)
        content = Path(out).read_text()
        assert "4" in content


def test_input_gen_relax_params():
    mod = _load_module("input_gen", INPUT_GEN_SCRIPT)
    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, "INCAR")
        mod.generate_incar("relax", {}, out)
        content = Path(out).read_text()
        assert "IBRION" in content
        assert "NSW" in content


def test_vasp_pymatgen_inputs():
    mod = _load_module("vasp_gen", VASP_SCRIPT)
    with tempfile.TemporaryDirectory() as tmpdir:
        result = mod.generate_vasp_inputs(
            str(FIXTURE_DIR / "POSCAR_Si"), "scf", tmpdir, kppa=100
        )
        assert result["status"] == "success"
        assert os.path.exists(os.path.join(tmpdir, "INCAR"))
        assert os.path.exists(os.path.join(tmpdir, "KPOINTS"))
        assert os.path.exists(os.path.join(tmpdir, "POSCAR"))
        assert result["num_atoms"] == 2


def test_vasp_pymatgen_relax():
    mod = _load_module("vasp_gen", VASP_SCRIPT)
    with tempfile.TemporaryDirectory() as tmpdir:
        result = mod.generate_vasp_inputs(
            str(FIXTURE_DIR / "POSCAR_Si"), "relax", tmpdir, kppa=100
        )
        assert result["status"] == "success"
        incar_content = Path(os.path.join(tmpdir, "INCAR")).read_text()
        assert "NSW" in incar_content


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        print(f"  {t.__name__}...", end=" ")
        t()
        print("OK")
    print(f"\n  All {len(tests)} tests passed!")
