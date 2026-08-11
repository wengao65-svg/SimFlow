#!/usr/bin/env python3
"""Focused tests for generic verification helper semantics."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from runtime.simflow_helpers.verification import generic as verification_helper


def test_run_verification_zero_checks_is_pending_not_pass():
    mod = verification_helper

    with tempfile.TemporaryDirectory() as tmpdir:
        result = mod.run_verification(tmpdir, stage="analysis_visualization")

    assert result["status"] == "success"
    assert result["verification_status"] == "pending"
    assert result["total_checks"] == 0
    assert result["all_passed"] is False
    assert result["reason_code"] == "no_checks_executed"
    assert "no verification checks" in result["message"].lower()
    assert result["simflow_result"]["role"] == "helper"
    assert result["simflow_result"]["activity"] == "verification"
    assert result["simflow_result"]["stage"] == "analysis_visualization"
    assert result["simflow_result"]["state_effect"] == "none"
    assert result["simflow_result"]["outcome"] == "waiting"
    assert result["simflow_result"]["reason_code"] == "no_checks_executed"


def test_run_verification_all_passed_maps_to_pass(monkeypatch):
    mod = verification_helper

    monkeypatch.setattr(mod, "verify_structure", lambda _: {"check": "structure_valid", "passed": True, "message": "ok"})
    monkeypatch.setattr(mod, "verify_convergence", lambda *_: {"check": "convergence", "passed": True, "message": "ok"})
    monkeypatch.setattr(mod, "verify_outputs_exist", lambda *_: {"check": "outputs_exist", "passed": True, "message": "ok"})

    with tempfile.TemporaryDirectory() as tmpdir:
        workflow_dir = Path(tmpdir)
        (workflow_dir / "POSCAR").write_text("placeholder", encoding="utf-8")
        outputs = workflow_dir / "outputs"
        outputs.mkdir()
        result = mod.run_verification(str(workflow_dir), stage="analysis_visualization", software="vasp", output_dir=str(outputs))

    assert result["status"] == "success"
    assert result["verification_status"] == "pass"
    assert result["all_passed"] is True
    assert result["passed"] == result["total_checks"] == 3
    assert result["simflow_result"]["outcome"] == "success"


def test_run_verification_failed_checks_map_to_fail(monkeypatch):
    mod = verification_helper

    monkeypatch.setattr(mod, "verify_structure", lambda _: {"check": "structure_valid", "passed": False, "message": "bad"})

    with tempfile.TemporaryDirectory() as tmpdir:
        workflow_dir = Path(tmpdir)
        (workflow_dir / "POSCAR").write_text("placeholder", encoding="utf-8")
        result = mod.run_verification(str(workflow_dir), stage="analysis_visualization")

    assert result["status"] == "success"
    assert result["verification_status"] == "fail"
    assert result["all_passed"] is False
    assert result["failed"] == 1
    assert result["simflow_result"]["outcome"] == "blocked"
