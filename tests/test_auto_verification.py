#!/usr/bin/env python3
"""Tests for P3.3 auto-verification on stage completion.

When update_stage(status=completed) is called, a verification record is
automatically created in verification.json with status='pending'.
"""

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runtime"))


def _init(project_root):
    from runtime.simflow_core.state import init_workflow
    return init_workflow("custom", "computation", project_root=project_root)


def test_stage_completion_creates_verification_record():
    """update_stage(completed) creates a verification record in verification.json."""
    from runtime.simflow_core.state import init_workflow, update_stage, read_state

    with tempfile.TemporaryDirectory() as tmpdir:
        init_workflow("custom", "computation", project_root=tmpdir)

        # Initially verification.json should be empty
        verification = read_state(project_root=tmpdir, state_file="verification.json")
        assert verification == [] or verification == {}

        # Mark stage as completed
        update_stage("computation", "completed", project_root=tmpdir)

        # verification.json should now have a record
        verification = read_state(project_root=tmpdir, state_file="verification.json")
        assert isinstance(verification, list)
        assert len(verification) >= 1
        entry = verification[-1]
        assert entry["stage"] == "computation"
        assert entry["status"] == "pending"
        assert "created_at" in entry


def test_stage_in_progress_does_not_create_verification():
    """update_stage(in_progress) does NOT create a verification record."""
    from runtime.simflow_core.state import init_workflow, update_stage, read_state

    with tempfile.TemporaryDirectory() as tmpdir:
        init_workflow("custom", "computation", project_root=tmpdir)

        update_stage("computation", "in_progress", project_root=tmpdir)

        verification = read_state(project_root=tmpdir, state_file="verification.json")
        assert verification == [] or verification == {}


def test_plain_stage_failure_does_not_create_completion_verification():
    """Failure lifecycle records a fail verification, not a completion record."""
    from runtime.simflow_core.state import init_workflow, update_stage, read_state

    with tempfile.TemporaryDirectory() as tmpdir:
        init_workflow("custom", "computation", project_root=tmpdir)

        update_stage("computation", "failed", project_root=tmpdir)

        verification = read_state(project_root=tmpdir, state_file="verification.json")
        assert verification == [] or verification == {}


def test_multiple_completions_create_multiple_records():
    """Multiple stage completions create multiple verification records."""
    from runtime.simflow_core.state import init_workflow, update_stage, read_state

    with tempfile.TemporaryDirectory() as tmpdir:
        init_workflow("custom", "computation", project_root=tmpdir)

        update_stage("computation", "completed", project_root=tmpdir)
        update_stage("analysis_visualization", "completed", project_root=tmpdir)

        verification = read_state(project_root=tmpdir, state_file="verification.json")
        assert isinstance(verification, list)
        assert len(verification) >= 2
        stages_verified = {v["stage"] for v in verification}
        assert "computation" in stages_verified
        assert "analysis_visualization" in stages_verified


def test_verification_does_not_require_checkpoint_binding():
    """Stage verification remains independent from recovery persistence."""
    from runtime.simflow_core.state import init_workflow, update_stage, read_state
    from runtime.simflow_core.checkpoints import create_checkpoint

    with tempfile.TemporaryDirectory() as tmpdir:
        state = init_workflow("custom", "computation", project_root=tmpdir)

        # Create a checkpoint first
        ckpt = create_checkpoint(
            workflow_id=state["workflow_id"],
            stage_id="computation",
            description="test checkpoint",
            project_root=tmpdir,
            run_id="run_test",
        )

        # Now mark stage as completed
        update_stage("computation", "completed", project_root=tmpdir)

        verification = read_state(project_root=tmpdir, state_file="verification.json")
        entry = verification[-1]
        assert entry.get("checkpoint_id") is None


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
