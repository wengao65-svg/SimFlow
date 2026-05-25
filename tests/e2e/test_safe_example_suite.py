"""Safe redistributable example coverage."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_safe_dry_run_example_produces_state_artifacts_checkpoints_and_handoff(tmp_path):
    result = subprocess.run(
        [
            "python",
            "examples/safe_dry_run/run_example.py",
            "--project-root",
            str(tmp_path),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    summary = json.loads(result.stdout)
    assert summary["status"] == "success"
    assert summary["current_stage"] == "writing"
    assert summary["workflow_status"] == "completed"
    assert summary["artifact_count"] >= 10
    assert summary["checkpoint_count"] >= 1
    assert summary["computation_readiness"] in {"blocked", "incomplete", "ready"}
    assert summary["dry_run_status"] in {"pass", "warning"}
    assert summary["hpc_submit_gate_status"] == "block"

    assert (tmp_path / ".simflow" / "state" / "workflow.json").is_file()
    assert (tmp_path / ".simflow" / "state" / "artifacts.json").is_file()
    assert (tmp_path / ".simflow" / "state" / "checkpoints.json").is_file()
    assert (tmp_path / ".simflow" / "artifacts" / "compute" / "dry_run_report.json").is_file()
    assert (tmp_path / ".simflow" / "artifacts" / "security" / "credential_scan.json").is_file()
    assert (tmp_path / ".simflow" / "reports" / "handoff" / "final_handoff.md").is_file()
    assert (tmp_path / ".simflow" / "reports" / "safe_example_summary.json").is_file()


def test_safe_examples_do_not_use_removed_runtime_lib_imports():
    for script in (ROOT / "examples").rglob("*.py"):
        text = script.read_text(encoding="utf-8")
        assert "from lib." not in text, str(script)
        assert "runtime/lib" not in text, str(script)
