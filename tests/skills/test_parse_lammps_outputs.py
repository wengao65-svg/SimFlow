#!/usr/bin/env python3
"""Tests for parse_lammps_outputs.py intake adapter."""

import json
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "skills" / "simflow-lammps" / "scripts"
FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures"
sys.path.insert(0, str(SCRIPT_DIR))


def _load_module():
    import importlib
    if "parse_lammps_outputs" in sys.modules:
        del sys.modules["parse_lammps_outputs"]
    import parse_lammps_outputs
    return parse_lammps_outputs


def _write_dump(path: Path, *, n_frames: int = 2, image_flags: bool = True, scaled: bool = False):
    cols = "id type"
    cols += " xs ys zs" if scaled else " x y z"
    if image_flags:
        cols += " ix iy iz"
    with open(path, "w") as fh:
        for i in range(n_frames):
            fh.write(f"ITEM: TIMESTEP\n{i * 100}\n")
            fh.write("ITEM: NUMBER OF ATOMS\n2\n")
            fh.write("ITEM: BOX BOUNDS pp pp pp\n0.0 10.0\n0.0 10.0\n0.0 10.0\n")
            fh.write(f"ITEM: ATOMS {cols}\n")
            fh.write("1 1 0.0 0.0 0.0 0 0 0\n" if image_flags else "1 1 0.0 0.0 0.0\n")
            fh.write("2 1 1.0 1.0 1.0 0 0 0\n" if image_flags else "2 1 1.0 1.0 1.0\n")


def _write_log(path: Path, *, units: str = "real", timestep: float = 1.0):
    with open(path, "w") as fh:
        fh.write(f"units {units}\n")
        fh.write(f"atom_style atomic\n")
        fh.write(f"timestep {timestep}\n")
        fh.write("Step Temp PotEng KinEng TotEng\n")
        fh.write("0 300.0 -10.0 0.5 -9.5\n")
        fh.write("100 305.0 -10.1 0.6 -9.5\n")


def _write_data(path: Path):
    with open(path, "w") as fh:
        fh.write("LAMMPS data file\n\n2 atoms\n1 atom types\n\nMasses\n\n1 28.085\n")


def test_parse_dump_header_counts_frames_and_detects_image_flags():
    mod = _load_module()
    with tempfile.TemporaryDirectory() as td:
        dump = Path(td) / "dump.lammps"
        _write_dump(dump, n_frames=3, image_flags=True)
        r = mod.parse_dump_header(dump)
        assert r["available"] is True
        assert r["frame_count"] == 3
        assert r["n_atoms"] == 2
        assert r["has_image_flags"] is True
        assert r["has_atom_ids"] is True
        assert r["has_types"] is True
        assert r["scaled_coords"] is False
        assert "x" in r["columns"]


def test_parse_dump_header_flags_scaled_coords_without_image_flags():
    mod = _load_module()
    with tempfile.TemporaryDirectory() as td:
        dump = Path(td) / "dump.lammps"
        _write_dump(dump, n_frames=2, image_flags=False, scaled=True)
        r = mod.parse_dump_header(dump)
        assert r["has_image_flags"] is False
        assert r["scaled_coords"] is True


def test_parse_log_extracts_units_and_thermo():
    mod = _load_module()
    with tempfile.TemporaryDirectory() as td:
        log = Path(td) / "log.lammps"
        _write_log(log, units="metal", timestep=0.5)
        r = mod.parse_log(log)
        assert r["available"] is True
        assert r["units_style"] == "metal"
        assert r["timestep_command"] == 0.5
        assert r["atom_style"] == "atomic"
        assert r["thermo"]["total_steps"] == 100
        assert r["thermo"]["converged"] is False
        assert any("cannot establish scientific convergence" in warning for warning in r["thermo"]["warnings"])


def test_build_intake_manifest_records_limitations_and_boundary():
    mod = _load_module()
    log = mod.parse_log(None)
    dump = mod.parse_dump_header(None)
    data = mod.parse_data_header(None)
    manifest = mod.build_intake_manifest(log=log, dump=dump, data=data, work_dir=Path("/tmp"))

    assert manifest["manifest_type"] == "lammps_output_intake_manifest"
    assert "log.lammps" in manifest["missing_inputs"]
    assert "dump trajectory" in manifest["missing_inputs"]
    assert "data/topology file" in manifest["missing_inputs"]
    assert "simflow-analysis-visualization" in manifest["boundary"]


def test_build_intake_manifest_flags_missing_image_flags_as_limitation():
    mod = _load_module()
    with tempfile.TemporaryDirectory() as td:
        log = Path(td) / "log.lammps"
        _write_log(log)
        dump = Path(td) / "dump.lammps"
        _write_dump(dump, n_frames=2, image_flags=False)
        data = Path(td) / "data.lammps"
        _write_data(data)

        manifest = mod.build_intake_manifest(
            log=mod.parse_log(log),
            dump=mod.parse_dump_header(dump),
            data=mod.parse_data_header(data),
            work_dir=Path(td),
        )
        joined = " ".join(manifest["limitations"])
        assert "image flags" in joined
        assert "md_structure" in manifest["recommended_analysis_family"]


def test_parse_lammps_outputs_writes_only_explicit_report(tmp_path):
    mod = _load_module()
    calc = tmp_path / "calc"
    calc.mkdir()
    _write_log(calc / "log.lammps")
    _write_dump(calc / "dump.lammps", n_frames=2, image_flags=True)
    _write_data(calc / "data.lammps")

    report = tmp_path / "intake.json"
    result = mod.parse_lammps_outputs(calc_dir=str(calc), report=str(report))

    assert result["status"] == "success"
    assert "simflow_result" not in result
    payload = json.loads(report.read_text())["intake_manifest"]
    assert payload["manifest_type"] == "lammps_output_intake_manifest"
    assert payload["source_files"]["dump"]["has_image_flags"] is True
    assert payload["source_files"]["log"]["units_style"] == "real"
    assert not (tmp_path / "reports").exists()
    assert not (tmp_path / ".simflow").exists()


def test_parse_lammps_outputs_returns_needs_inputs_when_files_missing(tmp_path):
    mod = _load_module()
    calc = tmp_path / "empty"
    calc.mkdir()

    result = mod.parse_lammps_outputs(calc_dir=str(calc))

    assert result["status"] == "needs_inputs"
    assert result["intake_manifest"]["missing_inputs"]
    assert not list(calc.iterdir())


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        print(f"  {t.__name__}...", end=" ")
        t()
        print("OK")
    print(f"\n  All {len(tests)} tests passed!")
