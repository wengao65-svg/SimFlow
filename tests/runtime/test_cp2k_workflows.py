#!/usr/bin/env python3
"""Tests for CP2K workflow classification and dry-run planning."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "runtime"))

from lib.cp2k_input import generate_input, write_xyz
from lib.cp2k_workflows import build_cp2k_task_plan, classify_cp2k_request


def _write_input_case(tmp_path: Path, task: str) -> None:
    coord = tmp_path / "structure.xyz"
    coord.write_text(write_xyz(2, "si", ["Si 0 0 0", "Si 1 1 1"]), encoding="utf-8")
    inp = tmp_path / f"{task}.inp"
    inp.write_text(
        generate_input(
            {
                "coord_file": "structure.xyz",
                "coord_path": str(coord),
                "elements": ["Si"],
            },
            task,
        ),
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    ("task_request", "expected"),
    [
        ("energy", "energy"),
        ("geo_opt", "geo_opt"),
        ("cell_opt", "cell_opt"),
        ("aimd_nvt", "aimd_nvt"),
        ("aimd_nve", "aimd_nve"),
        ("aimd_npt", "aimd_npt"),
        ("restart continuation", "restart"),
        ("parse outputs", "parse"),
        ("troubleshoot convergence", "troubleshoot"),
    ],
)
def test_classify_cp2k_request(task_request, expected):
    result = classify_cp2k_request(task_request, [])
    assert result["task"] == expected


def test_restart_requires_restart_file_label():
    result = classify_cp2k_request("restart", ["job.inp", "structure.xyz"])
    assert result["task"] == "restart"
    assert "restart_file" in result["missing_inputs"]


def test_parse_and_troubleshoot_use_log_requirement():
    parse_result = classify_cp2k_request("parse", ["job.log"])
    trouble_result = classify_cp2k_request("troubleshoot", ["job.log"])
    assert parse_result["missing_inputs"] == []
    assert trouble_result["missing_inputs"] == []


def test_build_plan_for_energy_is_dry_run(monkeypatch, tmp_path):
    monkeypatch.setattr("shutil.which", lambda name: None)
    _write_input_case(tmp_path, "energy")
    plan = build_cp2k_task_plan("energy", str(tmp_path), {"calc_dir": "."})
    assert plan["task"] == "energy"
    assert plan["validation_report"]["status"] == "pass"
    assert plan["compute_plan"]["dry_run"] is True
    assert plan["compute_plan"]["real_submit"] is False
    assert plan["compute_plan"]["runtime_detection"]["detected"] is False


def test_build_plan_for_geo_cell_and_aimd_tasks(monkeypatch, tmp_path):
    monkeypatch.setattr("shutil.which", lambda name: None)
    for task in ("geo_opt", "cell_opt", "aimd_nvt", "aimd_nve", "aimd_npt"):
        case_dir = tmp_path / task
        case_dir.mkdir()
        _write_input_case(case_dir, task)
        plan = build_cp2k_task_plan(task, str(case_dir), {"calc_dir": "."})
        assert plan["task"] == task
        assert plan["validation_report"]["status"] == "pass"
        assert plan["compute_plan"]["task"] == task


def test_build_plan_for_restart_detects_missing_restart(monkeypatch, tmp_path):
    monkeypatch.setattr("shutil.which", lambda name: None)
    _write_input_case(tmp_path, "aimd_nvt")
    inp = tmp_path / "aimd_nvt.inp"
    inp.write_text(inp.read_text(encoding="utf-8") + "\n&EXT_RESTART\n  RESTART_FILE_NAME missing.restart\n&END EXT_RESTART\n", encoding="utf-8")
    plan = build_cp2k_task_plan("restart", str(tmp_path), {"calc_dir": "."})
    assert plan["task"] == "restart"
    assert plan["validation_report"]["status"] == "fail"


def test_build_plan_for_parse_and_troubleshoot_without_input(monkeypatch, tmp_path):
    monkeypatch.setattr("shutil.which", lambda name: None)
    (tmp_path / "job.log").write_text("PROGRAM ENDED AT\n", encoding="utf-8")
    parse_plan = build_cp2k_task_plan("parse", str(tmp_path), {"calc_dir": "."})
    troubleshoot_plan = build_cp2k_task_plan("troubleshoot", str(tmp_path), {"calc_dir": "."})
    assert parse_plan["validation_report"]["status"] == "skip"
    assert troubleshoot_plan["validation_report"]["status"] == "skip"
