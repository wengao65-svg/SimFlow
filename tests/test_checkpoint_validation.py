#!/usr/bin/env python3
"""Tests for checkpoint stage upsert, snapshot enforcement, and stage_id validation.

Covers P1.2 + P1.3 + P1.4:
- P1.2: create_checkpoint auto-upserts canonical stage into stages.json
- P1.3: create_checkpoint enforces state_snapshot completeness
- P1.4: stage_id validation rejects non-canonical undeclared stages
"""

import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runtime"))


def _init(project_root):
    from runtime.simflow_core.state import init_workflow
    return init_workflow("custom", "computation", project_root=project_root)


# ============================================================
# P1.2: Auto-upsert stage into stages.json
# ============================================================

def test_checkpoint_auto_upserts_canonical_stage():
    """create_checkpoint auto-creates a canonical stage not yet in stages.json."""
    from runtime.simflow_core.checkpoints import create_checkpoint
    from runtime.simflow_core.state import read_state

    with tempfile.TemporaryDirectory() as tmpdir:
        state = _init(tmpdir)
        # stages.json should be empty {} at this point
        stages_before = read_state(project_root=tmpdir, state_file="stages.json")
        assert stages_before == {}

        create_checkpoint(
            workflow_id=state["workflow_id"],
            stage_id="computation",
            description="test checkpoint",
            project_root=tmpdir,
        )

        stages_after = read_state(project_root=tmpdir, state_file="stages.json")
        assert "computation" in stages_after
        assert stages_after["computation"]["stage_name"] == "computation"
        assert stages_after["computation"]["status"] == "in_progress"
        assert stages_after["computation"]["checkpoint_id"].startswith("ckpt_001_")


def test_checkpoint_updates_existing_stage_checkpoint_id():
    """create_checkpoint updates checkpoint_id on an already-declared stage."""
    from runtime.simflow_core.checkpoints import create_checkpoint
    from runtime.simflow_core.state import read_state, update_stage

    with tempfile.TemporaryDirectory() as tmpdir:
        state = _init(tmpdir)
        update_stage("computation", "in_progress", project_root=tmpdir)

        ckpt = create_checkpoint(
            workflow_id=state["workflow_id"],
            stage_id="computation",
            description="test checkpoint",
            project_root=tmpdir,
        )

        stages = read_state(project_root=tmpdir, state_file="stages.json")
        assert stages["computation"]["checkpoint_id"] == ckpt["checkpoint_id"]


# ============================================================
# P1.3: state_snapshot enforcement
# ============================================================

def test_checkpoint_rejects_empty_snapshot():
    """create_checkpoint rejects empty state_snapshot for non-failure status."""
    from runtime.simflow_core.checkpoints import create_checkpoint

    with tempfile.TemporaryDirectory() as tmpdir:
        state = _init(tmpdir)
        # Mock _snapshot_state to return empty dict
        from unittest.mock import patch
        with patch("runtime.simflow_core.checkpoints._snapshot_state", return_value={}):
            with pytest.raises(ValueError, match="state_snapshot is empty"):
                create_checkpoint(
                    workflow_id=state["workflow_id"],
                    stage_id="computation",
                    description="test",
                    project_root=tmpdir,
                )


def test_failure_checkpoint_allows_empty_snapshot():
    """create_checkpoint allows empty snapshot for failure status."""
    from runtime.simflow_core.checkpoints import create_checkpoint

    with tempfile.TemporaryDirectory() as tmpdir:
        state = _init(tmpdir)
        # Mock _snapshot_state to return empty dict
        from unittest.mock import patch
        with patch("runtime.simflow_core.checkpoints._snapshot_state", return_value={}):
            # Should NOT raise for failure checkpoints
            ckpt = create_checkpoint(
                workflow_id=state["workflow_id"],
                stage_id="computation",
                description="failure checkpoint",
                status="failure",
                project_root=tmpdir,
            )
            assert ckpt["status"] == "failure"


def test_checkpoint_rejects_missing_workflow_json():
    """create_checkpoint rejects snapshot missing workflow.json."""
    from runtime.simflow_core.checkpoints import create_checkpoint

    with tempfile.TemporaryDirectory() as tmpdir:
        state = _init(tmpdir)
        # Mock _snapshot_state to return a snapshot missing workflow.json
        from unittest.mock import patch
        incomplete_snapshot = {"stages.json": {}, "checkpoints.json": []}
        with patch("runtime.simflow_core.checkpoints._snapshot_state", return_value=dict(incomplete_snapshot)):
            with pytest.raises(ValueError, match="missing required files"):
                create_checkpoint(
                    workflow_id=state["workflow_id"],
                    stage_id="computation",
                    description="test",
                    project_root=tmpdir,
                )


# ============================================================
# P1.4: stage_id validation
# ============================================================

def test_checkpoint_rejects_non_canonical_undeclared_stage():
    """create_checkpoint rejects a non-canonical stage not in stages.json."""
    from runtime.simflow_core.checkpoints import create_checkpoint

    with tempfile.TemporaryDirectory() as tmpdir:
        state = _init(tmpdir)

        with pytest.raises(ValueError, match="not a canonical stage"):
            create_checkpoint(
                workflow_id=state["workflow_id"],
                stage_id="my_custom_stage",
                description="test",
                project_root=tmpdir,
            )


def test_checkpoint_accepts_declared_custom_stage():
    """create_checkpoint accepts a custom stage declared via update_stage."""
    from runtime.simflow_core.checkpoints import create_checkpoint
    from runtime.simflow_core.state import update_stage

    with tempfile.TemporaryDirectory() as tmpdir:
        state = _init(tmpdir)
        update_stage("my_custom_stage", "in_progress", project_root=tmpdir)

        ckpt = create_checkpoint(
            workflow_id=state["workflow_id"],
            stage_id="my_custom_stage",
            description="test",
            project_root=tmpdir,
        )
        assert ckpt["stage_id"] == "my_custom_stage"


def test_failure_checkpoint_allows_non_canonical_stage():
    """Failure checkpoints can use non-canonical undeclared stage_ids."""
    from runtime.simflow_core.checkpoints import create_checkpoint

    with tempfile.TemporaryDirectory() as tmpdir:
        state = _init(tmpdir)

        with pytest.warns(UserWarning, match="non-canonical undeclared"):
            ckpt = create_checkpoint(
                workflow_id=state["workflow_id"],
                stage_id="unknown_failure_stage",
                description="failure checkpoint",
                status="failure",
                project_root=tmpdir,
            )
        assert ckpt["stage_id"] == "unknown_failure_stage"
        assert ckpt["status"] == "failure"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
