"""Tests for compact checkpoint compatibility behavior."""

import json
from pathlib import Path

import pytest

from runtime.simflow_core.checkpoints import (
    create_checkpoint,
    get_latest_checkpoint,
    list_checkpoints,
    restore_checkpoint,
)
from runtime.simflow_core.state import init_workflow, read_state, write_state


def test_create_recoverable_checkpoint_uses_restart_references(tmp_path):
    workflow = init_workflow("dft", "computation", project_root=str(tmp_path))
    restart = tmp_path / "restart.wfn"
    restart.write_text("restart\n", encoding="utf-8")

    checkpoint = create_checkpoint(
        workflow["workflow_id"],
        "computation",
        "Resume calculation",
        project_root=str(tmp_path),
        restart_refs=["restart.wfn"],
        resume_command="solver --restart restart.wfn",
    )

    assert checkpoint["status"] == "success"
    assert checkpoint["recoverable"] is True
    assert checkpoint["storage"] == "compact_reference"
    assert "state_snapshot" not in checkpoint
    assert "lineage_snapshot" not in checkpoint
    assert checkpoint["simflow_result"]["activity"] == "create_checkpoint"


def test_stage_boundary_without_recovery_refs_is_diagnostic(tmp_path):
    workflow = init_workflow("dft", "modeling", project_root=str(tmp_path))
    checkpoint = create_checkpoint(
        workflow["workflow_id"], "modeling", "Stage boundary", project_root=str(tmp_path)
    )
    assert checkpoint["status"] == "failure"
    assert checkpoint["recovery_status"] == "diagnostic"
    assert checkpoint["recoverable"] is False
    with pytest.raises(ValueError, match="diagnostic-only"):
        restore_checkpoint(checkpoint["checkpoint_id"], project_root=str(tmp_path))


def test_list_and_latest_read_compact_files(tmp_path):
    workflow = init_workflow("dft", "computation", project_root=str(tmp_path))
    first = create_checkpoint(
        workflow["workflow_id"], "computation", "first", project_root=str(tmp_path), run_id="run_1"
    )
    second = create_checkpoint(
        workflow["workflow_id"], "analysis", "second", project_root=str(tmp_path), run_id="run_2"
    )
    assert [item["checkpoint_id"] for item in list_checkpoints(project_root=str(tmp_path))] == [
        first["checkpoint_id"], second["checkpoint_id"]
    ]
    assert get_latest_checkpoint(project_root=str(tmp_path))["checkpoint_id"] == second["checkpoint_id"]


def test_recover_validates_hash_without_rolling_back_state(tmp_path):
    workflow = init_workflow("dft", "computation", project_root=str(tmp_path))
    restart = tmp_path / "restart.dat"
    restart.write_text("v1\n", encoding="utf-8")
    checkpoint = create_checkpoint(
        workflow["workflow_id"], "computation", "resume", project_root=str(tmp_path),
        restart_refs=["restart.dat"], resume_command="solver restart.dat",
    )
    workflow_state = read_state(project_root=str(tmp_path), state_file="workflow.json")
    workflow_state["status"] = "changed_after_checkpoint"
    write_state(workflow_state, project_root=str(tmp_path), state_file="workflow.json")

    restored = restore_checkpoint(checkpoint["checkpoint_id"], project_root=str(tmp_path))

    assert restored["state_restored"] is False
    assert restored["recovery_validation"]["ready"] is True
    assert read_state(project_root=str(tmp_path), state_file="workflow.json")["status"] == "changed_after_checkpoint"


def test_recover_reports_hash_mismatch(tmp_path):
    workflow = init_workflow("dft", "computation", project_root=str(tmp_path))
    restart = tmp_path / "restart.dat"
    restart.write_text("v1\n", encoding="utf-8")
    checkpoint = create_checkpoint(
        workflow["workflow_id"], "computation", "resume", project_root=str(tmp_path),
        restart_refs=["restart.dat"], resume_command="solver restart.dat",
    )
    restart.write_text("v2\n", encoding="utf-8")
    restored = restore_checkpoint(checkpoint["checkpoint_id"], project_root=str(tmp_path))
    assert restored["recovery_validation"]["ready"] is False
    assert restored["recovery_validation"]["issues"][0]["status"] == "hash_mismatch"


def test_legacy_snapshot_checkpoint_is_listed_read_only(tmp_path):
    checkpoint_dir = tmp_path / ".simflow" / "checkpoints"
    checkpoint_dir.mkdir(parents=True)
    legacy = {
        "checkpoint_id": "ckpt_legacy",
        "stage_id": "modeling",
        "status": "success",
        "state_snapshot": {"workflow.json": {"status": "old"}},
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    (checkpoint_dir / "ckpt_legacy.json").write_text(json.dumps(legacy), encoding="utf-8")
    listed = list_checkpoints(project_root=str(tmp_path))
    assert listed[0]["legacy_read_only"] is True
    assert listed[0]["recoverable"] is False
    with pytest.raises(ValueError, match="read-only"):
        restore_checkpoint("ckpt_legacy", project_root=str(tmp_path))


def test_checkpoint_does_not_mutate_legacy_registries(tmp_path):
    workflow = init_workflow("dft", "computation", project_root=str(tmp_path))
    state_dir = tmp_path / ".simflow" / "state"
    before = {name: (state_dir / name).read_bytes() for name in ("stages.json", "checkpoints.json", "lineage.json")}
    create_checkpoint(
        workflow["workflow_id"], "custom_stage", "compact", project_root=str(tmp_path), run_id="run_1"
    )
    assert {name: (state_dir / name).read_bytes() for name in before} == before


def test_checkpoint_rejects_invalid_status(tmp_path):
    workflow = init_workflow("dft", "computation", project_root=str(tmp_path))
    with pytest.raises(ValueError, match="Unsupported checkpoint status"):
        create_checkpoint(workflow["workflow_id"], "computation", "bad", project_root=str(tmp_path), status="warning")


def test_restore_missing_checkpoint(tmp_path):
    with pytest.raises(FileNotFoundError):
        restore_checkpoint("ckpt_missing", project_root=str(tmp_path))
