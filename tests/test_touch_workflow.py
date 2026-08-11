#!/usr/bin/env python3
"""Tests for touch_workflow auto-refresh of state timestamps.

Covers P1.1 + P1.5:
- touch_workflow refreshes workflow.json.updated_at, summary.json.updated_at,
  and status_summary.md after state changes
- create_checkpoint auto-propagates to summary.json (fixes S6->S14 amnesia)
- update_stage auto-refreshes workflow state
- register_artifact auto-refreshes workflow state
- status_summary.md contains live stage/artifact/checkpoint counts
"""

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runtime"))


def _init(project_root):
    from runtime.simflow_core.state import init_workflow
    return init_workflow("custom", "computation", project_root=project_root)


def _read(project_root, state_file):
    from runtime.simflow_core.state import read_state
    return read_state(project_root=project_root, state_file=state_file)


def test_touch_workflow_updates_timestamps():
    """touch_workflow refreshes workflow.json and summary.json updated_at."""
    from runtime.simflow_core.state import touch_workflow

    with tempfile.TemporaryDirectory() as tmpdir:
        _init(tmpdir)
        wf_before = _read(tmpdir, "workflow.json")
        summary_before = _read(tmpdir, "summary.json")

        # Simulate time passing
        import time
        time.sleep(0.01)

        touch_workflow(tmpdir)

        wf_after = _read(tmpdir, "workflow.json")
        summary_after = _read(tmpdir, "summary.json")

        assert wf_after["updated_at"] != wf_before["updated_at"]
        assert summary_after["updated_at"] != summary_before["updated_at"]


def test_touch_workflow_regenerates_status_summary():
    """touch_workflow regenerates status_summary.md with live counts."""
    from runtime.simflow_core.state import touch_workflow

    with tempfile.TemporaryDirectory() as tmpdir:
        _init(tmpdir)
        report_path = Path(tmpdir) / ".simflow" / "reports" / "status_summary.md"
        original = report_path.read_text(encoding="utf-8")
        assert "Status: initialized" in original

        # Add some state
        from runtime.simflow_core.state import update_stage
        update_stage("computation", "in_progress", project_root=tmpdir)

        # touch_workflow should have been called by update_stage
        content = report_path.read_text(encoding="utf-8")
        assert "computation: in_progress" in content
        assert "Artifacts:" in content
        assert "Checkpoints:" in content


def test_create_checkpoint_updates_compact_summary_not_legacy_summary():
    """Compact checkpoints leave legacy summary timestamps unchanged."""
    from runtime.simflow_core.state import init_workflow, read_state
    from runtime.simflow_core.checkpoints import create_checkpoint

    with tempfile.TemporaryDirectory() as tmpdir:
        state = init_workflow("custom", "computation", project_root=tmpdir)
        summary_before = read_state(project_root=tmpdir, state_file="summary.json")
        updated_at_before = summary_before["updated_at"]

        import time
        time.sleep(0.01)

        create_checkpoint(
            workflow_id=state["workflow_id"],
            stage_id="computation",
            description="test checkpoint",
            project_root=tmpdir,
            run_id="run_test",
        )

        summary_after = read_state(project_root=tmpdir, state_file="summary.json")
        project = json.loads((Path(tmpdir) / ".simflow" / "project.json").read_text(encoding="utf-8"))
        assert summary_after["updated_at"] == updated_at_before
        assert project["counts"]["by_kind"]["checkpoint"] == 1


def test_register_artifact_updates_compact_summary_not_legacy_workflow():
    """Logical artifact records leave legacy workflow timestamps unchanged."""
    from runtime.simflow_core.state import init_workflow, read_state
    from runtime.simflow_core.artifacts import register_artifact

    with tempfile.TemporaryDirectory() as tmpdir:
        state = init_workflow("custom", "computation", project_root=tmpdir)
        wf_before = read_state(project_root=tmpdir, state_file="workflow.json")
        updated_at_before = wf_before["updated_at"]

        import time
        time.sleep(0.01)

        # Create a test file
        test_file = Path(tmpdir) / "output.txt"
        test_file.write_text("test", encoding="utf-8")

        register_artifact(
            "output.txt", "output_file", "computation",
            path="output.txt", project_root=tmpdir,
        )

        wf_after = read_state(project_root=tmpdir, state_file="workflow.json")
        project = json.loads((Path(tmpdir) / ".simflow" / "project.json").read_text(encoding="utf-8"))
        assert wf_after["updated_at"] == updated_at_before
        assert project["counts"]["by_kind"]["artifact"] == 1


def test_update_stage_propagates_to_workflow():
    """update_stage auto-refreshes workflow.json.updated_at."""
    from runtime.simflow_core.state import init_workflow, read_state, update_stage

    with tempfile.TemporaryDirectory() as tmpdir:
        init_workflow("custom", "computation", project_root=tmpdir)
        wf_before = read_state(project_root=tmpdir, state_file="workflow.json")
        updated_at_before = wf_before["updated_at"]

        import time
        time.sleep(0.01)

        update_stage("computation", "in_progress", project_root=tmpdir)

        wf_after = read_state(project_root=tmpdir, state_file="workflow.json")
        assert wf_after["updated_at"] != updated_at_before


def test_touch_workflow_updates_current_stage():
    """touch_workflow can optionally update current_stage."""
    from runtime.simflow_core.state import touch_workflow, read_state

    with tempfile.TemporaryDirectory() as tmpdir:
        _init(tmpdir)
        wf_before = read_state(tmpdir, "workflow.json")
        assert wf_before["current_stage"] == "computation"

        touch_workflow(tmpdir, current_stage="analysis_visualization")

        wf_after = read_state(tmpdir, "workflow.json")
        assert wf_after["current_stage"] == "analysis_visualization"


def test_status_summary_shows_non_canonical_stages():
    """status_summary.md includes custom stages declared via update_stage."""
    from runtime.simflow_core.state import update_stage

    with tempfile.TemporaryDirectory() as tmpdir:
        _init(tmpdir)
        # Declare a custom stage
        update_stage("my_custom_stage", "in_progress", project_root=tmpdir)

        report = (Path(tmpdir) / ".simflow" / "reports" / "status_summary.md").read_text(encoding="utf-8")
        assert "my_custom_stage" in report
        assert "in_progress" in report


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
