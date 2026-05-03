#!/usr/bin/env python3
"""Tests for make_supercell.py skill script."""

import json
import os
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "skills" / "simflow-modeling" / "scripts"
FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures"
sys.path.insert(0, str(SCRIPT_DIR))


def test_2x2x2_supercell():
    from make_supercell import make_supercell
    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, "POSCAR_super")
        result = make_supercell(str(FIXTURE_DIR / "POSCAR_Si"), [2, 2, 2], out)
        assert result["status"] == "success"
        assert result["original_atoms"] == 2
        assert result["supercell_atoms"] == 16
        assert result["scale_matrix"] == [2, 2, 2]


def test_3x1x1_supercell():
    from make_supercell import make_supercell
    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, "POSCAR_super")
        result = make_supercell(str(FIXTURE_DIR / "POSCAR_Si"), [3, 1, 1], out)
        assert result["supercell_atoms"] == 6


def test_cif_output():
    from make_supercell import make_supercell
    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, "super.cif")
        result = make_supercell(str(FIXTURE_DIR / "POSCAR_Si"), [2, 2, 2], out, fmt="cif")
        assert result["status"] == "success"
        assert os.path.exists(out)


def test_lattice_scaling():
    from make_supercell import make_supercell
    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, "POSCAR_super")
        result = make_supercell(str(FIXTURE_DIR / "POSCAR_Si"), [2, 2, 2], out)
        # Original Si lattice ~3.84 Angstrom, 2x should be ~7.68
        assert result["lattice_parameters"]["a"] > 5.0
        assert result["lattice_parameters"]["b"] > 5.0
        assert result["lattice_parameters"]["c"] > 5.0


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        print(f"  {t.__name__}...", end=" ")
        t()
        print("OK")
    print(f"\n  All {len(tests)} tests passed!")
