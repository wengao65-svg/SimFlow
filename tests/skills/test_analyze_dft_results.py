"""Tests for the analyze_dft_results helper boundary."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills" / "simflow-vasp" / "scripts" / "analyze_dft_results.py"


def test_analyze_dft_results_only_supports_its_vasp_parser():
    source = SCRIPT.read_text(encoding="utf-8")

    assert "QEParser" not in source
    assert 'choices=["vasp"]' in source
    assert '"qe"' not in source
