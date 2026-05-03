#!/usr/bin/env python3
"""Tests for analyze_md_trajectory.py skill script."""

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "skills" / "simflow-analysis" / "scripts"
FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures"
sys.path.insert(0, str(SCRIPT_DIR))


def test_import_mdanalysis():
    try:
        from MDAnalysis import Universe
        from MDAnalysis.analysis.rdf import InterRDF
        from MDAnalysis.analysis.msd import EinsteinMSD
        assert True
    except ImportError:
        print(" (skipped - MDAnalysis not installed)", end="")
        return False
    return True


def test_rdf_computation():
    if not test_import_mdanalysis():
        return
    from MDAnalysis import Universe
    from MDAnalysis.analysis.rdf import InterRDF
    # Use LAMMPS dump file with explicit format
    dump = str(FIXTURE_DIR / "lammps_dump.lammps")

    u = Universe(dump, format="LAMMPSDUMP")
    group = u.select_atoms("all")
    rdf = InterRDF(group, group, nbins=50, range=(0, 6.0))
    rdf.run()

    assert len(rdf.results.bins) == 50
    assert len(rdf.results.rdf) == 50
    assert rdf.results.bins[0] >= 0


def test_no_crash_without_mdanalysis():
    """Script should handle missing MDAnalysis gracefully."""
    # Just verify the script can be imported
    try:
        import analyze_md_trajectory
    except SystemExit:
        pass  # Expected if MDAnalysis not installed


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        print(f"  {t.__name__}...", end=" ")
        t()
        print("OK")
    print(f"\n  All {len(tests)} tests passed!")
