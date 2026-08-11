"""Safe redistributable compact-runtime example coverage."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _run_example(script: str, tmp_path: Path) -> dict:
    result = subprocess.run(
        ["python", script, "--project-root", str(tmp_path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def _assert_compact_state(tmp_path: Path, summary: dict) -> None:
    assert summary["status"] == "success"
    assert summary["submit_blocked"] is True
    assert summary["approval_required"] is True
    assert summary["record_count"] == 1
    assert summary["checkpoint_count"] == 0
    assert len(summary["run_plan_hash"]) == 64
    assert summary["credential_scan_status"] in {"pass", "warning"}
    assert (tmp_path / ".simflow" / "project.json").is_file()
    assert (tmp_path / ".simflow" / "records.jsonl").is_file()
    assert not (tmp_path / ".simflow" / "state").exists()
    assert not (tmp_path / ".simflow" / "checkpoints").exists()
    assert (tmp_path / summary["important_paths"]["run_plan"]).is_file()


def test_safe_dry_run_example_uses_one_compact_record(tmp_path):
    summary = _run_example("examples/safe_dry_run/run_example.py", tmp_path)
    _assert_compact_state(tmp_path, summary)
    assert (tmp_path / "calculation" / "job.sh").is_file()
    assert (tmp_path / ".simflow" / "reports" / "safe_example_summary.json").is_file()


def test_lammps_safe_dry_run_example_uses_one_compact_record(tmp_path):
    summary = _run_example("examples/lammps_safe_dry_run/run_example.py", tmp_path)
    _assert_compact_state(tmp_path, summary)
    assert summary["software"] == "lammps"
    assert summary["real_submit"] is False
    assert (tmp_path / "calculation" / "lammps_safe" / "in.lammps").is_file()
    assert (tmp_path / "calculation" / "lammps_safe" / "data.lammps").is_file()
    assert (tmp_path / ".simflow" / "reports" / "lammps_safe_example_summary.json").is_file()


def test_safe_examples_do_not_use_removed_runtime_lib_imports():
    for script in (ROOT / "examples").rglob("*.py"):
        text = script.read_text(encoding="utf-8")
        assert "from lib." not in text, str(script)
        assert "runtime/lib" not in text, str(script)
