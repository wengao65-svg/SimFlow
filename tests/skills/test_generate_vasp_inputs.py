#!/usr/bin/env python3
"""Tests for generate_vasp_inputs.py skill scripts."""

import importlib
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures"
INPUT_GEN_SCRIPT = Path(__file__).resolve().parents[2] / "skills" / "simflow-computation" / "scripts" / "generate_vasp_inputs.py"
VASP_SCRIPT = Path(__file__).resolve().parents[2] / "skills" / "simflow-vasp" / "scripts" / "generate_vasp_inputs.py"

pytestmark = pytest.mark.filterwarnings(
    "ignore:Set OLD_ERROR_HANDLING to false and catch the errors directly\\.:DeprecationWarning"
)


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


# ── NBANDS policy tests ───────────────────────────────────────

def test_scf_no_nbands():
    """SCF INCAR should not contain NBANDS (ordinary calc, no POTCAR)."""
    mod = _load_module("vasp_gen", VASP_SCRIPT)
    with tempfile.TemporaryDirectory() as tmpdir:
        result = mod.generate_vasp_inputs(
            str(FIXTURE_DIR / "POSCAR_Si"), "scf", tmpdir, kppa=100
        )
        assert result["status"] == "success"
        incar_content = Path(os.path.join(tmpdir, "INCAR")).read_text()
        assert "NBANDS" not in incar_content


def test_bands_no_nbands():
    """Bands INCAR should not contain NBANDS (ordinary calc)."""
    mod = _load_module("vasp_gen", VASP_SCRIPT)
    with tempfile.TemporaryDirectory() as tmpdir:
        result = mod.generate_vasp_inputs(
            str(FIXTURE_DIR / "POSCAR_Si"), "bands", tmpdir, kppa=100
        )
        assert result["status"] == "success"
        incar_content = Path(os.path.join(tmpdir, "INCAR")).read_text()
        assert "NBANDS" not in incar_content


def test_optics_has_nbands_with_nelect():
    """Optics INCAR should contain NBANDS when NELECT is provided."""
    mod = _load_module("vasp_gen", VASP_SCRIPT)
    with tempfile.TemporaryDirectory() as tmpdir:
        # Si 2-atom: ZVAL=4 -> NELECT=8, nions=2
        result = mod.generate_vasp_inputs(
            str(FIXTURE_DIR / "POSCAR_Si"), "optics", tmpdir,
            params={"NELECT": 8}, kppa=100,
        )
        assert result["status"] == "success"
        incar_content = Path(os.path.join(tmpdir, "INCAR")).read_text()
        assert "NBANDS" in incar_content
        # Should be > occupied_bands (ceil(8/2)=4)
        for line in incar_content.split("\n"):
            if "NBANDS" in line and "=" in line:
                nbands_val = int(line.split("=")[1].strip())
                assert nbands_val > 4


def test_user_nbands_preserved():
    """User-explicit NBANDS=20 should be preserved when valid."""
    mod = _load_module("vasp_gen", VASP_SCRIPT)
    with tempfile.TemporaryDirectory() as tmpdir:
        result = mod.generate_vasp_inputs(
            str(FIXTURE_DIR / "POSCAR_Si"), "scf", tmpdir,
            params={"NELECT": 8, "NBANDS": 20}, kppa=100,
        )
        assert result["status"] == "success"
        incar_content = Path(os.path.join(tmpdir, "INCAR")).read_text()
        assert "NBANDS" in incar_content
        assert "20" in incar_content


def test_user_nbands_too_small_raises():
    """User-explicit NBANDS=4 with NELECT=8 (occupied=4) should raise."""
    mod = _load_module("vasp_gen", VASP_SCRIPT)
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            mod.generate_vasp_inputs(
                str(FIXTURE_DIR / "POSCAR_Si"), "scf", tmpdir,
                params={"NELECT": 8, "NBANDS": 4}, kppa=100,
            )
            assert False, "Should have raised ValueError"
        except (ValueError, SystemExit):
            pass  # Expected


def test_residual_nbands_removed_in_scf():
    """Residual NBANDS in params should be removed for ordinary SCF."""
    mod = _load_module("vasp_gen", VASP_SCRIPT)
    with tempfile.TemporaryDirectory() as tmpdir:
        # Pass NBANDS="auto" (sentinel -> treated as not specified)
        result = mod.generate_vasp_inputs(
            str(FIXTURE_DIR / "POSCAR_Si"), "scf", tmpdir,
            params={"NELECT": 8, "NBANDS": "auto"}, kppa=100,
        )
        assert result["status"] == "success"
        incar_content = Path(os.path.join(tmpdir, "INCAR")).read_text()
        # "auto" sentinel -> policy removes NBANDS
        assert "NBANDS" not in incar_content


# ── NCORE / NPAR policy tests ─────────────────────────────────

def test_vasp_generator_unknown_context_omits_ncore_npar():
    mod = _load_module("vasp_gen_ncore_unknown", VASP_SCRIPT)
    with tempfile.TemporaryDirectory() as tmpdir:
        result = mod.generate_vasp_inputs(
            str(FIXTURE_DIR / "POSCAR_Si"), "scf", tmpdir, kppa=100
        )
        assert result["status"] == "success"
        incar_content = Path(os.path.join(tmpdir, "INCAR")).read_text()
        assert "NCORE" not in incar_content
        assert "NPAR" not in incar_content
        assert result["incar_policy"]["ncore_npar"]["status"] == "needs_inputs"


def test_vasp_generator_cpu_context_defaults_to_npar():
    mod = _load_module("vasp_gen_ncore_cpu", VASP_SCRIPT)
    with tempfile.TemporaryDirectory() as tmpdir:
        result = mod.generate_vasp_inputs(
            str(FIXTURE_DIR / "POSCAR_Si"), "scf", tmpdir,
            params={"execution_mode": "cpu"}, kppa=100,
        )
        assert result["status"] == "success"
        incar_content = Path(os.path.join(tmpdir, "INCAR")).read_text()
        assert "NPAR" in incar_content
        assert "4" in incar_content
        assert "execution_mode" not in incar_content


def test_vasp_generator_accelerated_context_omits_ncore_npar():
    mod = _load_module("vasp_gen_ncore_gpu", VASP_SCRIPT)
    with tempfile.TemporaryDirectory() as tmpdir:
        result = mod.generate_vasp_inputs(
            str(FIXTURE_DIR / "POSCAR_Si"), "scf", tmpdir,
            params={"execution_mode": "openacc"}, kppa=100,
        )
        assert result["status"] == "success"
        incar_content = Path(os.path.join(tmpdir, "INCAR")).read_text()
        assert "NCORE" not in incar_content
        assert "NPAR" not in incar_content
        assert result["incar_policy"]["ncore_npar"]["execution_context"] == "accelerated"


def test_template_generator_unknown_context_omits_unresolved_blocks_and_ncore():
    mod = _load_module("input_gen_ncore_unknown", INPUT_GEN_SCRIPT)
    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, "INCAR")
        mod.generate_incar("scf", {"job_name": "test"}, out)
        content = Path(out).read_text()
        assert "{%" not in content
        assert "NCORE" not in content
        assert "NPAR" not in content


def test_template_generator_cpu_context_writes_npar_not_ncore():
    mod = _load_module("input_gen_ncore_cpu", INPUT_GEN_SCRIPT)
    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, "INCAR")
        mod.generate_incar("scf", {"job_name": "test", "execution_mode": "cpu"}, out)
        content = Path(out).read_text()
        assert "NPAR" in content
        assert "4" in content
        assert "NCORE" not in content


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        print(f"  {t.__name__}...", end=" ")
        t()
        print("OK")
    print(f"\n  All {len(tests)} tests passed!")
