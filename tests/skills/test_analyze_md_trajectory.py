#!/usr/bin/env python3
"""Tests for analyze_md_trajectory.py skill script."""

import json
import sys
import tempfile
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "skills" / "simflow-analysis-visualization" / "scripts"
FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures"
sys.path.insert(0, str(SCRIPT_DIR))


def _load_module():
    import importlib
    if "analyze_md_trajectory" in sys.modules:
        del sys.modules["analyze_md_trajectory"]
    import analyze_md_trajectory
    return analyze_md_trajectory


def _write_dump_file(path: Path, n_frames: int = 3, n_atoms: int = 2, image_flags: bool = True):
    cols = "id type x y z"
    if image_flags:
        cols += " ix iy iz"
    with open(path, "w") as fh:
        for f in range(n_frames):
            fh.write(f"ITEM: TIMESTEP\n{f * 100}\n")
            fh.write(f"ITEM: NUMBER OF ATOMS\n{n_atoms}\n")
            fh.write("ITEM: BOX BOUNDS pp pp pp\n0.0 10.0\n0.0 10.0\n0.0 10.0\n")
            fh.write(f"ITEM: ATOMS {cols}\n")
            for i in range(1, n_atoms + 1):
                if image_flags:
                    fh.write(f"{i} 1 {float(i + f)} {float(i + f)} {float(i + f)} 0 0 0\n")
                else:
                    fh.write(f"{i} 1 {float(i + f)} {float(i + f)} {float(i + f)}\n")


def test_import_mdanalysis():
    pytest.importorskip("MDAnalysis")
    from MDAnalysis import Universe
    from MDAnalysis.analysis.rdf import InterRDF
    from MDAnalysis.analysis.msd import EinsteinMSD

    assert Universe is not None
    assert InterRDF is not None
    assert EinsteinMSD is not None


def test_no_crash_without_mdanalysis():
    try:
        _load_module()
    except SystemExit:
        pass


def test_build_analysis_quality_manifest_warns_without_provenance():
    mod = _load_module()

    manifest = mod.build_analysis_quality_manifest(
        n_frames=8,
        timestep=None,
        timestep_units=None,
        equilibration_start=None,
        analyses=["msd", "rdf"],
        error_estimates={},
    )

    assert manifest["claim_scope"] == "analysis_support_only"
    assert manifest["n_frames"] == 8
    assert manifest["timestep"] is None
    assert manifest["timestep_units"] is None
    warning_codes = {item["code"] for item in manifest["warnings"]}
    assert warning_codes == {
        "insufficient_frames_for_statistics",
        "timestep_not_recorded",
        "equilibration_boundary_not_recorded",
        "analysis_error_estimates_missing",
    }


def test_build_analysis_quality_manifest_includes_intake_warnings():
    mod = _load_module()

    intake_warnings = [{"code": "some_intake_limitation", "message": "m"}]
    manifest = mod.build_analysis_quality_manifest(
        n_frames=20,
        timestep=1.0,
        timestep_units="ps",
        equilibration_start=5,
        analyses=["msd"],
        intake_warnings=intake_warnings,
        error_estimates={"msd": "block"},
    )

    codes = {item["code"] for item in manifest["warnings"]}
    assert "some_intake_limitation" in codes
    assert "insufficient_frames_for_statistics" not in codes
    assert "equilibration_boundary_not_recorded" not in codes
    assert "analysis_error_estimates_missing" not in codes


@pytest.mark.filterwarnings("ignore:Guessed all Masses:UserWarning")
@pytest.mark.filterwarnings("ignore:Reader has no dt:UserWarning")
def test_inspect_trajectory_intake_warns_on_missing_timestep_units():
    pytest.importorskip("MDAnalysis")
    mod = _load_module()

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        dump = td / "dump.lammpstrj"
        _write_dump_file(dump, n_frames=3, image_flags=True)

        u = mod.load_universe(str(dump), str(dump),
                               topology_format="LAMMPSDUMP", trajectory_format="LAMMPSDUMP")
        try:
            intake = mod.inspect_trajectory_intake(u, timestep_units=None)
            assert intake["n_frames"] == 3
            assert intake["timestep_units"] is None
            codes = {w["code"] for w in intake["warnings"]}
            assert "timestep_units_not_specified" in codes
        finally:
            u.trajectory.close()


@pytest.mark.filterwarnings("ignore:Guessed all Masses:UserWarning")
@pytest.mark.filterwarnings("ignore:Reader has no dt:UserWarning")
def test_analyze_trajectory_attaches_quality_manifest_and_loads_once():
    pytest.importorskip("MDAnalysis")
    mod = _load_module()

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        dump = td / "dump.lammpstrj"
        _write_dump_file(dump, n_frames=3, image_flags=True)

        load_count = {"n": 0}
        real_load = mod.load_universe

        def counting_load(topology, trajectory, **kwargs):
            load_count["n"] += 1
            return real_load(topology, trajectory, **kwargs)

        mod.load_universe = counting_load
        try:
            result = mod.analyze_trajectory(
                str(dump), str(dump), ["rdf", "msd"],
                rdf_params={"nbins": 20, "rmax": 5.0},
                timestep_units="ps",
                equilibration_start=0,
                topology_format="LAMMPSDUMP",
                trajectory_format="LAMMPSDUMP",
            )
        finally:
            mod.load_universe = real_load

    assert load_count["n"] == 1
    assert result["analysis_quality"]["claim_scope"] == "analysis_support_only"
    assert "rdf" in result["analyses"]
    assert "msd" in result["analyses"]
    assert result["analyses"]["msd"]["equilibration_start"] == 0
    assert result["analyses"]["msd"]["timestep_units"] == "ps"


@pytest.mark.filterwarnings("ignore:Guessed all Masses:UserWarning")
@pytest.mark.filterwarnings("ignore:Reader has no dt:UserWarning")
def test_compute_msd_units_aware_conversion_only_for_ps():
    pytest.importorskip("MDAnalysis")
    mod = _load_module()

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        dump = td / "dump.lammpstrj"
        _write_dump_file(dump, n_frames=3, image_flags=True)

        u_ps = mod.load_universe(str(dump), str(dump),
                                  topology_format="LAMMPSDUMP", trajectory_format="LAMMPSDUMP")
        try:
            res_ps = mod.compute_msd(u_ps, equilibration_start=0, timestep_units="ps")
        finally:
            u_ps.trajectory.close()

        assert res_ps["timestep_units"] == "ps"
        if res_ps["diffusion_coefficient_raw"] is not None:
            expected = res_ps["diffusion_coefficient_raw"] * 1e-4
            assert abs(res_ps["diffusion_coefficient_cm2_per_s"] - expected) < 1e-30
            assert res_ps["diffusion_coefficient_ang2_per_ps"] is not None
        else:
            assert res_ps["diffusion_coefficient_cm2_per_s"] is None

        u_lj = mod.load_universe(str(dump), str(dump),
                                  topology_format="LAMMPSDUMP", trajectory_format="LAMMPSDUMP")
        try:
            res_lj = mod.compute_msd(u_lj, equilibration_start=0, timestep_units="lj")
        finally:
            u_lj.trajectory.close()

        assert res_lj["diffusion_coefficient_cm2_per_s"] is None
        assert res_lj["diffusion_coefficient_ang2_per_ps"] is None


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        print(f"  {t.__name__}...", end=" ")
        t()
        print("OK")
    print(f"\n  All {len(tests)} tests passed!")
