#!/usr/bin/env python3
"""Tests for the LAMMPS trajectory analysis helper."""

from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "skills" / "simflow-lammps" / "scripts" / "analyze_lammps_trajectory.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("simflow_lammps_analyze_test", str(SCRIPT_PATH))
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_analysis_quality_manifest_warns_without_timestep_equilibration_or_error_estimates():
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


def test_analyze_lammps_attaches_analysis_quality_manifest(monkeypatch):
    mod = _load_module()

    class FakeTrajectory:
        dt = None

        def __len__(self):
            return 4

    class FakeAtoms:
        def __len__(self):
            return 2

    class FakeUniverse:
        trajectory = FakeTrajectory()
        atoms = FakeAtoms()

    monkeypatch.setattr(mod, "load_lammps_universe", lambda data_file, dump_file: FakeUniverse())

    result = mod.analyze_lammps("data.lammps", "dump.lammpstrj", [], timestep_units=None)

    assert result["analysis_quality"]["claim_scope"] == "analysis_support_only"
    assert result["analysis_quality"]["n_frames"] == 4
    warning_codes = {item["code"] for item in result["analysis_quality"]["warnings"]}
    assert "insufficient_frames_for_statistics" in warning_codes
    assert "equilibration_boundary_not_recorded" in warning_codes
