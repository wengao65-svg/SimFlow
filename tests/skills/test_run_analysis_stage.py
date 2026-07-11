#!/usr/bin/env python3
"""Focused tests for analysis-stage trajectory recognition."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills" / "simflow-analysis-visualization" / "scripts" / "run_analysis_stage.py"
sys.path.insert(0, str(ROOT))


def _load_module():
    spec = importlib.util.spec_from_file_location("simflow_run_analysis_stage", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_trajectory_status_recognizes_dump_lammps(monkeypatch):
    mod = _load_module()
    monkeypatch.setattr(mod.importlib.util, "find_spec", lambda _: None)

    result = mod._trajectory_status("md", ["outputs/log.lammps", "outputs/dump.lammps"])

    assert result["status"] == "skipped_optional_dependency"


def test_trajectory_status_recognizes_lammpstrj_dump_extensions(monkeypatch):
    mod = _load_module()
    monkeypatch.setattr(mod.importlib.util, "find_spec", lambda _: None)

    for path in ["traj/run.lammpstrj", "traj/production.dump", "nested/dump.segment.0001"]:
        result = mod._trajectory_status("aimd_nvt", [path])
        assert result["status"] == "skipped_optional_dependency", path


def test_trajectory_status_rejects_obvious_nontrajectory_dump_notes(monkeypatch):
    mod = _load_module()
    monkeypatch.setattr(mod.importlib.util, "find_spec", lambda _: None)

    result = mod._trajectory_status("md", ["outputs/log.lammps", "outputs/dump_notes.txt"])

    assert result["status"] == "missing_trajectory"
