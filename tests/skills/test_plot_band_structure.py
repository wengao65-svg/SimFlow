#!/usr/bin/env python3
"""Tests for plot_band_structure.py (moved to simflow-analysis-visualization)."""

import sys
import tempfile
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "skills" / "simflow-analysis-visualization" / "scripts"
FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures"
sys.path.insert(0, str(SCRIPT_DIR))


def _load_module():
    import importlib
    if "plot_band_structure" in sys.modules:
        del sys.modules["plot_band_structure"]
    import plot_band_structure
    return plot_band_structure


def _write_line_mode_kpoints(path: Path):
    path.write_text(
        "K-Path\n8\nLine-mode\nreciprocal\n"
        "0.0 0.0 0.0 ! G\n"
        "0.5 0.0 0.0 ! X\n"
        "0.5 0.5 0.0 ! M\n"
        "0.0 0.0 0.0 ! G\n"
    )


def test_parse_kpoints_labels_extracts_labeled_points():
    mod = _load_module()

    with tempfile.TemporaryDirectory() as td:
        kp = Path(td) / "KPOINTS"
        _write_line_mode_kpoints(kp)
        labels = mod.parse_kpoints_labels(str(kp))

    assert len(labels) == 4
    coords, lbls = zip(*labels)
    assert list(lbls) == ["G", "X", "M", "G"]
    assert coords[0] == [0.0, 0.0, 0.0]
    assert coords[1] == [0.5, 0.0, 0.0]


def test_compute_segment_boundaries_matches_labeled_points():
    mod = _load_module()
    kcoords = [[0.0, 0, 0], [0.1, 0, 0], [0.5, 0, 0], [0.5, 0.5, 0]]
    labeled = [([0.0, 0, 0], "G"), ([0.5, 0, 0], "X"), ([0.5, 0.5, 0], "M")]
    boundaries = mod.compute_segment_boundaries(kcoords, labeled)

    idxs = [i for i, _ in boundaries]
    lbls = [l for _, l in boundaries]
    assert 0 in idxs and 2 in idxs and 3 in idxs
    assert "G" in lbls and "X" in lbls and "M" in lbls


def test_detect_segment_boundaries_finds_distance_jumps():
    mod = _load_module()
    kcoords = [[0, 0, 0], [0.1, 0, 0], [0.2, 0, 0], [0.8, 0, 0], [0.9, 0, 0]]
    distances = [0.0, 0.1, 0.2, 0.8, 0.9]
    boundaries = mod.detect_segment_boundaries(kcoords, distances)
    assert 0 in boundaries
    assert 3 in boundaries


def test_plot_band_structure_renders_from_eigenval_fixture(tmp_path):
    pytest.importorskip("matplotlib")
    mod = _load_module()
    eigenval = FIXTURE_DIR / "EIGENVAL_Si"
    if not eigenval.exists():
        pytest.skip("EIGENVAL_Si fixture missing")

    output = tmp_path / "bands.png"
    out = mod.plot_band_structure(
        eigenval_path=str(eigenval),
        kpoints_path=None,
        output_path=str(output),
        efermi=6.0,
        emin=-10.0,
        emax=10.0,
        show=False,
    )

    assert out == str(output)
    assert output.exists()
    assert output.stat().st_size > 0


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        print(f"  {t.__name__}...", end=" ")
        t()
        print("OK")
    print(f"\n  All {len(tests)} tests passed!")
