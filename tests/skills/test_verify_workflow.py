#!/usr/bin/env python3
"""Tests for final delivery verification workflow script."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = ROOT / "skills" / "simflow-verify" / "scripts"
RUNTIME_TEST_DIR = ROOT / "tests" / "runtime"
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(RUNTIME_TEST_DIR))
sys.path.insert(0, str(ROOT))

from runtime.lib.state import init_workflow
from runtime.lib.verification import REQUIRED_CHECK_NAMES
from test_verification import _write_final_delivery_state
from verify_workflow import verify_workflow


def test_verify_workflow_generates_report_and_registers_artifact():
    with tempfile.TemporaryDirectory() as tmpdir:
        init_workflow("dft", "literature", tmpdir)
        _write_final_delivery_state(tmpdir)

        result = verify_workflow(str(Path(tmpdir) / ".simflow"))
        report_path = Path(tmpdir) / ".simflow" / "reports" / "verify" / "verification_report.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))

        assert result["status"] == "success"
        assert result["verification_status"] == "pass"
        assert report_path.is_file()
        assert {artifact["name"] for artifact in result["artifacts"]} == {"verification_report.json"}
        assert {check["name"] for check in report["checks"]} == set(REQUIRED_CHECK_NAMES)
        assert report["status"] == "pass"


def test_verify_workflow_cli_runs_and_emits_json():
    with tempfile.TemporaryDirectory() as tmpdir:
        init_workflow("dft", "literature", tmpdir)
        _write_final_delivery_state(tmpdir, include_redacted_secret=True)

        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_DIR / "verify_workflow.py"),
                "--workflow-dir",
                str(Path(tmpdir) / ".simflow"),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        payload = json.loads(completed.stdout)
        report_path = Path(tmpdir) / ".simflow" / "reports" / "verify" / "verification_report.json"

        assert completed.returncode == 0
        assert payload["status"] == "success"
        assert payload["verification_status"] == "warning"
        assert report_path.is_file()
