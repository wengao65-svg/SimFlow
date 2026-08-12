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
    assert summary["record_count"] == 2
    assert summary["checkpoint_count"] == 0
    assert len(summary["run_plan_hash"]) == 64
    assert summary["credential_scan_status"] in {"pass", "warning"}
    assert (tmp_path / ".simflow" / "project.json").is_file()
    assert (tmp_path / ".simflow" / "records.jsonl").is_file()
    records = [json.loads(line) for line in (tmp_path / ".simflow" / "records.jsonl").read_text(encoding="utf-8").splitlines()]
    assert records[0]["details"]["operation"] == "plan"
    assert records[1]["kind"] in {"artifact", "milestone", "run"}
    assert not (tmp_path / ".simflow" / "state").exists()
    assert not (tmp_path / ".simflow" / "checkpoints").exists()
    assert (tmp_path / summary["important_paths"]["run_plan"]).is_file()


def test_safe_dry_run_example_records_plan_and_deliverable(tmp_path):
    summary = _run_example("examples/safe_dry_run/run_example.py", tmp_path)
    _assert_compact_state(tmp_path, summary)
    assert (tmp_path / "calculation" / "job.sh").is_file()
    assert (tmp_path / ".simflow" / "reports" / "safe_example_summary.json").is_file()


def test_lammps_safe_dry_run_example_records_plan_and_deliverable(tmp_path):
    summary = _run_example("examples/lammps_safe_dry_run/run_example.py", tmp_path)
    _assert_compact_state(tmp_path, summary)
    assert summary["software"] == "lammps"
    assert summary["real_submit"] is False
    assert (tmp_path / "calculation" / "lammps_safe" / "in.lammps").is_file()
    assert (tmp_path / "calculation" / "lammps_safe" / "data.lammps").is_file()
    assert (tmp_path / ".simflow" / "reports" / "lammps_safe_example_summary.json").is_file()


def test_h2o_cp2k_example_only_generates_local_inputs(tmp_path):
    result = subprocess.run(
        [
            "python",
            "examples/h2o/run_cp2k_workflow.py",
            "--dry-run",
            "--output-dir",
            str(tmp_path),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    summary = json.loads(result.stdout)
    assert summary["status"] == "prepared"
    assert summary["real_execution"] is False
    assert summary["generated_files"] == ["aimd/aimd_nvt.inp", "aimd/structure.xyz"]
    assert (tmp_path / "dry_run_summary.json").is_file()
    assert not (tmp_path / ".simflow").exists()


def test_safe_examples_do_not_use_removed_runtime_lib_imports():
    for script in (ROOT / "examples").rglob("*.py"):
        text = script.read_text(encoding="utf-8")
        assert "from lib." not in text, str(script)
        assert "runtime/lib" not in text, str(script)


def test_examples_do_not_bypass_public_hpc_runtime():
    forbidden = (
        'subprocess.run(["ssh"',
        'subprocess.run(["scp"',
        " sbatch ",
        "ssh ${",
        "scp ${",
        "--submit",
    )
    offenders = []
    for script in (ROOT / "examples").rglob("*"):
        if not script.is_file() or script.suffix not in {".py", ".sh"}:
            continue
        text = script.read_text(encoding="utf-8")
        matches = [token for token in forbidden if token in text]
        if matches:
            offenders.append((str(script.relative_to(ROOT)), matches))
    assert offenders == []
