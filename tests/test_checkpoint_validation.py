"""Validation tests for compact recovery references."""

import json

import pytest

from runtime.simflow_core.checkpoints import create_checkpoint
from runtime.simflow_core.records import create_recovery_checkpoint, inspect_project
from runtime.simflow_core.state import init_workflow, read_state


def test_ready_checkpoint_requires_recovery_reference(tmp_path):
    with pytest.raises(ValueError, match="recovery reference"):
        create_recovery_checkpoint(str(tmp_path), summary="empty")


def test_diagnostic_checkpoint_allows_no_reference(tmp_path):
    checkpoint = create_recovery_checkpoint(str(tmp_path), summary="diagnostic", status="diagnostic")
    assert checkpoint["status"] == "diagnostic"


def test_legacy_adapter_accepts_custom_stage_without_stage_registry_mutation(tmp_path):
    workflow = init_workflow("custom", "computation", project_root=str(tmp_path))
    checkpoint = create_checkpoint(
        workflow["workflow_id"], "custom_analysis", "resume", project_root=str(tmp_path), run_id="run_1"
    )
    assert checkpoint["stage_id"] == "custom_analysis"
    assert read_state(project_root=str(tmp_path), state_file="stages.json") == {}


def test_checkpoint_contains_offset_and_no_registry_snapshot(tmp_path):
    checkpoint = create_recovery_checkpoint(
        str(tmp_path), summary="resume", run_id="run_1", resume_command="solver --resume"
    )
    stored = json.loads(
        (tmp_path / ".simflow" / "checkpoints" / f"{checkpoint['checkpoint_id']}.json").read_text(encoding="utf-8")
    )
    assert isinstance(stored["records_offset"], int)
    assert "state_snapshot" not in stored
    assert "lineage_snapshot" not in stored
    assert "artifact_versions" not in stored


def test_restricted_reference_stores_no_path(tmp_path):
    restricted = tmp_path / "licensed" / "POTCAR"
    restricted.parent.mkdir()
    restricted.write_text("restricted\n", encoding="utf-8")
    checkpoint = create_recovery_checkpoint(
        str(tmp_path), summary="restricted input metadata", run_id="run_1",
        input_refs=[{"path": "licensed/POTCAR", "restricted": True, "name": "POTCAR", "dataset": "Fe_pv"}],
    )
    ref = checkpoint["input_refs"][0]
    assert ref["path"] == "[RESTRICTED PATH]"
    assert ref["sha256"]


def test_project_summary_tracks_latest_checkpoint(tmp_path):
    checkpoint = create_recovery_checkpoint(
        str(tmp_path), summary="latest", run_id="run_1", resume_command="resume"
    )
    project = inspect_project(str(tmp_path))["project"]
    assert project["current"]["latest_checkpoint_id"] == checkpoint["checkpoint_id"]


def test_checkpoint_record_is_single_logical_event(tmp_path):
    create_recovery_checkpoint(str(tmp_path), summary="one event", run_id="run_1", resume_command="resume")
    inspected = inspect_project(str(tmp_path))
    assert inspected["record_count"] == 1
    assert inspected["records"][0]["kind"] == "checkpoint"
