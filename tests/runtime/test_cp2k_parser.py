#!/usr/bin/env python3
"""Tests for CP2K output parsing."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "runtime"))

from lib.parsers.cp2k_parser import CP2KParser


FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "cp2k"


def test_parse_log_normal_end_and_energy():
    parser = CP2KParser()
    result = parser.parse(str(FIXTURE_DIR / "md.log"))
    assert result.converged is True
    assert result.metadata["normal_end"] is True
    assert result.metadata["cp2k_version"] == "2026.1"
    assert result.metadata["run_type"] == "MD"
    assert result.metadata["project_name"] == "MD_SAMPLE"
    assert result.final_energy == -17.05


def test_parse_log_detects_scf_converged():
    parser = CP2KParser()
    result = parser.parse(str(FIXTURE_DIR / "md.log"))
    assert result.metadata["scf_converged"] is True
    assert result.metadata["scf_converged_steps"] == 2


def test_parse_log_detects_abort(tmp_path):
    parser = CP2KParser()
    log_path = tmp_path / "abort.log"
    log_path.write_text(
        "CP2K| version string: CP2K version 2026.1\nGLOBAL| Run type ENERGY\nABORT: bad SCF\n",
        encoding="utf-8",
    )
    result = parser.parse(str(log_path))
    assert result.converged is False
    assert result.metadata["abort_detected"] is True
    assert result.errors


def test_parse_ener_extracts_temperature_conserved_quantity_and_used_time():
    parser = CP2KParser()
    data = parser.parse_ener(str(FIXTURE_DIR / "md.ener"))
    assert data["steps"] == [1, 2]
    assert data["md_steps"] == 2
    assert data["final_temperature"] == 301.2
    assert data["final_conserved_quantity"] == -16.94
    assert data["final_used_time"] == 1.1


def test_parse_trajectory_last_frame():
    parser = CP2KParser()
    frames = parser.parse_trajectory(str(FIXTURE_DIR / "md-pos-1.xyz"))
    assert len(frames) == 2
    assert frames[-1]["step"] == 1
    assert frames[-1]["time"] == 0.5
    assert frames[-1]["energy"] == -17.05
    assert frames[-1]["atoms"][0]["element"] == "O"


def test_parse_restart_metadata():
    parser = CP2KParser()
    metadata = parser.parse_restart_metadata(str(FIXTURE_DIR / "md.restart"))
    assert metadata["project_name"] == "MD_SAMPLE"
    assert metadata["run_type"] == "MD"
    assert metadata["step_start_val"] == 25
    assert metadata["restart_file_name"] == "MD_SAMPLE-1.restart"


def test_parse_outputs_collects_summary():
    parser = CP2KParser()
    result = parser.parse_outputs(str(FIXTURE_DIR))
    assert result["status"] == "parsed"
    summary = result["summary"]
    assert summary["cp2k_version"] == "2026.1"
    assert summary["run_type"] == "MD"
    assert summary["final_energy"] == -17.05
    assert summary["temperature"] == 301.2
    assert summary["conserved_quantity"] == -16.94
    assert summary["md_steps"] == 2
    assert summary["last_frame"]["step"] == 1
