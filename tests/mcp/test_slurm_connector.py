#!/usr/bin/env python3
"""Tests for SLURM connector enhancements: submit, sacct fallback, wait."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "mcp" / "servers" / "hpc"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "runtime"))

from connectors.slurm import SlurmConnector
from run_plan import build_run_plan
from runtime.simflow_core.gates import record_gate_decision


def _authorized_submit_kwargs(script_path: str) -> dict:
    project_root = Path(script_path).parent
    input_file = project_root / "input.dat"
    input_file.write_text("input\n", encoding="utf-8")
    connector = SlurmConnector()
    plan = build_run_plan(
        str(project_root),
        {
            "script_path": Path(script_path).name,
            "input_paths": [input_file.name],
            "scheduler": "slurm",
        },
        script=Path(script_path),
        script_generated=False,
        validation=connector.dry_run(script_path),
    )
    decision = record_gate_decision(
        "hpc_submit",
        "approved",
        {
            "reason": "pytest submit authorization",
            "run_plan_hash": plan["run_plan_hash"],
        },
        project_root=str(project_root),
        agent="pytest",
    )
    return {
        "project_root": str(project_root),
        "gate_decision_id": decision["decision_id"],
        "run_plan_hash": plan["run_plan_hash"],
    }


@pytest.fixture
def connector():
    return SlurmConnector()


@pytest.fixture
def slurm_script(tmp_path):
    script = tmp_path / "test_job.sh"
    script.write_text("#!/bin/bash\n#SBATCH --job-name=test\nmpirun echo hello\n")
    return str(script)


class TestSubmit:
    def test_submit_requires_approval(self, connector, slurm_script):
        """submit() without a gate approval reference returns approval_required error."""
        result = connector.submit(slurm_script)
        assert result["status"] == "error"
        assert result["approval_required"] is True
        assert result["gate"] == "hpc_submit"

    def test_boolean_approved_does_not_bypass_gate(self, connector, slurm_script):
        """Legacy boolean approval is not sufficient for real submit."""
        result = connector.submit(slurm_script, approved=True)
        assert result["status"] == "error"
        assert result["approval_required"] is True
        assert result["gate"] == "hpc_submit"
        assert "Boolean approved is not accepted" in result["message"]

    def test_submit_script_not_found(self, connector):
        """submit() with nonexistent script returns error."""
        result = connector.submit("/nonexistent/path.sh", approved=True)
        assert result["status"] == "error"
        assert "not found" in result["message"].lower()

    @patch("subprocess.run")
    def test_submit_sbatch_success(self, mock_run, connector, slurm_script):
        """submit() with approval calls sbatch and returns job_id."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="Submitted batch job 12345\n", stderr=""
        )
        result = connector.submit(slurm_script, **_authorized_submit_kwargs(slurm_script))
        assert result["status"] == "success"
        assert result["job_id"] == "12345"
        assert result["gate_decision_id"].startswith("gate_decision_")
        assert len(result["script_hash"]) == 64
        assert result["run_plan_hash"]
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "sbatch"

    @patch("subprocess.run")
    def test_submit_sbatch_failure(self, mock_run, connector, slurm_script):
        """submit() handles sbatch failure."""
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="sbatch: error: Batch job submission failed"
        )
        result = connector.submit(slurm_script, **_authorized_submit_kwargs(slurm_script))
        assert result["status"] == "error"
        assert "sbatch failed" in result["message"]

    @patch("subprocess.run", side_effect=FileNotFoundError)
    def test_submit_sbatch_not_installed(self, mock_run, connector, slurm_script):
        """submit() handles sbatch not installed."""
        result = connector.submit(slurm_script, **_authorized_submit_kwargs(slurm_script))
        assert result["status"] == "error"
        assert "sbatch not found" in result["message"]

    def test_submit_blocks_modified_script_after_planning(self, connector, slurm_script):
        """Changing a script after planning invalidates approval reuse."""
        kwargs = _authorized_submit_kwargs(slurm_script)
        Path(slurm_script).write_text(
            "#!/bin/bash\n#SBATCH --job-name=changed\nmpirun echo changed\n",
            encoding="utf-8",
        )
        result = connector.submit(slurm_script, **kwargs)
        assert result["status"] == "error"
        assert result["code"] == "run_plan_stale"
        assert result["approval_required"] is True


class TestStatus:
    @patch("subprocess.run")
    def test_status_squeue_active(self, mock_run, connector):
        """status() returns squeue data for active jobs."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="RUNNING 0:05:30 node01\n", stderr=""
        )
        result = connector.status("12345")
        assert result["status"] == "success"
        assert result["data"]["state"] == "RUNNING"
        assert result["data"]["runtime"] == "0:05:30"
        assert result["data"]["nodes"] == "node01"

    @patch("subprocess.run")
    def test_status_squeue_not_found_falls_back_to_sacct(self, mock_run, connector):
        """status() falls back to sacct when squeue returns nothing."""
        mock_run.side_effect = [
            # squeue returns empty (job finished)
            MagicMock(returncode=0, stdout="", stderr=""),
            # sacct returns completed job
            MagicMock(
                returncode=0,
                stdout="COMPLETED|00:05:30|0:0|2024-01-01T00:00:00|2024-01-01T00:05:30\n",
                stderr="",
            ),
        ]
        result = connector.status("12345")
        assert result["status"] == "success"
        assert result["data"]["state"] == "COMPLETED"
        assert result["data"]["elapsed"] == "00:05:30"
        assert result["data"]["exit_code"] == "0:0"

    @patch("subprocess.run")
    def test_status_sacct_skips_batch_steps(self, mock_run, connector):
        """status() sacct parsing skips .batch and .extern steps."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),
            MagicMock(
                returncode=0,
                stdout=(
                    "COMPLETED|00:05:30|0:0||\n"
                    "COMPLETED|00:05:30|0:0||\n"
                    "COMPLETED|00:05:30|0:0||\n"
                ),
                stderr="",
            ),
        ]
        result = connector.status("12345")
        assert result["status"] == "success"
        assert result["data"]["state"] == "COMPLETED"

    @patch("subprocess.run")
    def test_status_not_found(self, mock_run, connector):
        """status() returns NOT_FOUND when both squeue and sacct have nothing."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
        result = connector.status("99999")
        assert result["status"] == "success"
        assert result["data"]["state"] == "NOT_FOUND"

    @patch("subprocess.run")
    def test_status_sacct_failed_job(self, mock_run, connector):
        """status() correctly reports FAILED state from sacct."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),
            MagicMock(
                returncode=0,
                stdout="FAILED|01:23:45|1:0||\n",
                stderr="",
            ),
        ]
        result = connector.status("54321")
        assert result["data"]["state"] == "FAILED"
        assert result["data"]["exit_code"] == "1:0"


class TestWait:
    @patch("subprocess.run")
    def test_wait_completes(self, mock_run, connector):
        """wait() returns when job reaches terminal state."""
        mock_run.side_effect = [
            # First poll: running
            MagicMock(returncode=0, stdout="RUNNING 0:01:00 node01\n", stderr=""),
            # Second poll: completed (squeue empty, sacct has result)
            MagicMock(returncode=0, stdout="", stderr=""),
            MagicMock(
                returncode=0,
                stdout="COMPLETED|00:05:30|0:0||\n",
                stderr="",
            ),
        ]
        result = connector.wait("12345", poll_interval=0, timeout=60)
        assert result["data"]["state"] == "COMPLETED"

    @patch("time.sleep")
    @patch("time.time")
    @patch("subprocess.run")
    def test_wait_timeout(self, mock_run, mock_time, mock_sleep, connector):
        """wait() returns timeout when job doesn't finish in time."""
        # Simulate time passing: start=0, first poll=1, second poll=3 (exceeds timeout=2)
        mock_time.side_effect = [0, 1, 3]
        mock_run.return_value = MagicMock(
            returncode=0, stdout="RUNNING 0:01:00 node01\n", stderr=""
        )
        result = connector.wait("12345", poll_interval=1, timeout=2)
        assert result["status"] == "timeout"
        assert "Timed out" in result["message"]


class TestDryRun:
    def test_dry_run_valid_script(self, connector, slurm_script):
        """dry_run() validates a script with SBATCH directives."""
        result = connector.dry_run(slurm_script)
        assert result["overall"] == "pass"
        assert result["dry_run"] is True
        assert len(result["script_hash"]) == 64

    def test_dry_run_missing_script(self, connector):
        """dry_run() fails for nonexistent script."""
        result = connector.dry_run("/nonexistent/path.sh")
        assert result["status"] == "fail"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
