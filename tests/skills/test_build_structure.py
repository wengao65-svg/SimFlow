#!/usr/bin/env python3
"""Tests for build_structure.py skill script."""

import json
import os
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "skills" / "simflow-modeling" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))


def test_from_type_fcc():
    from build_structure import build_from_type
    s = build_from_type("fcc", 4.05, ["Al"])
    assert len(s) == 1
    assert str(s[0].specie) == "Al"


def test_from_type_bcc():
    from build_structure import build_from_type
    s = build_from_type("bcc", 3.16, ["Fe"])
    assert len(s) == 2
    assert str(s[0].specie) == "Fe"


def test_from_type_diamond():
    from build_structure import build_from_type
    s = build_from_type("diamond", 5.43, ["Si"])
    assert len(s) == 2


def test_from_type_rocksalt():
    from build_structure import build_from_type
    s = build_from_type("rocksalt", 5.63, ["Na", "Cl"])
    assert len(s) == 2


def test_from_type_zincblende():
    from build_structure import build_from_type
    s = build_from_type("zincblende", 5.65, ["Ga", "As"])
    assert len(s) == 2


def test_from_type_unknown():
    from build_structure import build_from_type
    try:
        build_from_type("unknown", 5.0, ["Si"])
        assert False, "Should raise ValueError"
    except ValueError:
        pass


def test_from_params():
    from build_structure import build_from_params
    s = build_from_params(5.43, 5.43, 5.43, 90, 90, 90, ["Si", "Si"], [[0, 0, 0], [0.25, 0.25, 0.25]])
    assert len(s) == 2


def test_from_file():
    from build_structure import build_from_file
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "POSCAR_Si"
    s = build_from_file(str(fixture))
    assert len(s) == 2
    assert str(s[0].specie) == "Si"


def test_main_from_type():
    from build_structure import main
    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, "POSCAR")
        old_argv = sys.argv
        sys.argv = ["build_structure.py", "from_type", "--type", "fcc", "--lattice-param", "4.05",
                    "--elements", "Al", "--output", out]
        try:
            main()
            assert os.path.exists(out)
        finally:
            sys.argv = old_argv


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        print(f"  {t.__name__}...", end=" ")
        t()
        print("OK")
    print(f"\n  All {len(tests)} tests passed!")
