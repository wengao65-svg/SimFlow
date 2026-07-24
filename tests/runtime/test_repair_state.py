"""Tests for conservative SimFlow state audit and repair."""

import json
from pathlib import Path

import pytest

from runtime.simflow_core.repair import apply_state_repair, audit_state
from runtime.simflow_core.state import init_workflow, read_state, write_state


def _fixture(root: Path) -> str:
    workflow = init_workflow("custom", "literature_review", project_root=str(root))
    artifact_path = root / "result.dat"
    artifact_path.write_text("result\n", encoding="utf-8")
    artifact = {
        "artifact_id": "art_12345678",
        "name": "result.dat",
        "type": "analysis_output",
        "version": "v1.0.0",
        "stage": "analysis_visualization",
        "path": str(artifact_path),
        "lineage": {"parent_artifacts": [], "parameters": {}, "software": None},
        "metadata": {},
        "checksum": None,
        "created_at": "2026-07-24T00:00:00+00:00",
    }
    write_state([artifact], project_root=str(root), state_file="artifacts.json")
    write_state({"artifacts": [], "links": []}, project_root=str(root), state_file="lineage.json")
    checkpoint = {
        "checkpoint_id": "ckpt_001_analysis_visualization",
        "workflow_id": workflow["workflow_id"],
        "stage_id": "analysis_visualization",
        "status": "completed",
        "path": ".simflow/checkpoints/ckpt_001_analysis_visualization.json",
        "created_at": "2026-07-24T01:00:00+00:00",
    }
    write_state([checkpoint], project_root=str(root), state_file="checkpoints.json")
    checkpoint_file = root / checkpoint["path"]
    checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_file.write_text(json.dumps({
        **checkpoint,
        "state_snapshot": {"workflow.json": workflow, "stages.json": {}},
        "artifact_versions": {},
        "lineage_snapshot": {"artifacts": [], "links": []},
    }), encoding="utf-8")
    return workflow["workflow_id"]


def _tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted((root / ".simflow").rglob("*"))
        if path.is_file()
    }


def test_audit_is_read_only_and_reports_deterministic_rules(tmp_path):
    _fixture(tmp_path)
    before = _tree_bytes(tmp_path)
    report = audit_state(str(tmp_path))
    after = _tree_bytes(tmp_path)

    assert before == after
    assert report["mode"] == "audit"
    assert report["backup_path"] is None
    assert report["report_path"] is None
    rule_ids = {item["rule_id"] for item in report["eligible_findings"]}
    assert "artifact.fill_workflow_id" in rule_ids
    assert "lineage.create_missing_node" in rule_ids
    assert "stage.declare_canonical" in rule_ids
    assert "checkpoint.sync_registry_file_metadata" in rule_ids


def test_apply_backs_up_repairs_and_is_idempotent(tmp_path):
    workflow_id = _fixture(tmp_path)
    result = apply_state_repair(str(tmp_path))

    artifacts = read_state(project_root=str(tmp_path), state_file="artifacts.json")
    lineage = read_state(project_root=str(tmp_path), state_file="lineage.json")
    stages = read_state(project_root=str(tmp_path), state_file="stages.json")
    workflow = read_state(project_root=str(tmp_path), state_file="workflow.json")
    checkpoints = read_state(project_root=str(tmp_path), state_file="checkpoints.json")

    assert result["changed"] is True
    assert Path(result["backup_path"]).is_dir()
    assert (tmp_path / result["report_path"]).is_file()
    assert artifacts[0]["workflow_id"] == workflow_id
    assert lineage["artifacts"][0]["artifact_id"] == "art_12345678"
    assert "art_12345678" in stages["analysis_visualization"]["outputs"]
    assert stages["analysis_visualization"]["last_success_checkpoint_id"] == "ckpt_001_analysis_visualization"
    assert checkpoints[0]["status"] == "success"
    assert checkpoints[0]["legacy_status"] == "completed"
    assert checkpoints[0]["recoverable"] is True
    assert workflow["status"] == "in_progress"
    assert workflow["current_stage"] == "analysis_visualization"

    second = apply_state_repair(str(tmp_path))
    assert second["changed"] is False
    assert second["backup_path"] is None


def test_incomplete_checkpoint_never_becomes_recovery_success(tmp_path):
    _fixture(tmp_path)
    checkpoint_path = tmp_path / ".simflow" / "checkpoints" / "ckpt_001_analysis_visualization.json"
    payload = json.loads(checkpoint_path.read_text())
    payload["state_snapshot"] = {}
    checkpoint_path.write_text(json.dumps(payload), encoding="utf-8")

    apply_state_repair(str(tmp_path))
    checkpoints = read_state(project_root=str(tmp_path), state_file="checkpoints.json")
    stages = read_state(project_root=str(tmp_path), state_file="stages.json")
    assert checkpoints[0]["status"] == "partial"
    assert checkpoints[0]["recoverable"] is False
    assert stages["analysis_visualization"].get("last_success_checkpoint_id") is None


def test_threshold_must_be_greater_than_point_eight(tmp_path):
    _fixture(tmp_path)
    with pytest.raises(ValueError, match="greater than 0.8"):
        audit_state(str(tmp_path), min_confidence=0.8)


def test_checkpoint_registry_file_status_conflict_is_audit_only(tmp_path):
    _fixture(tmp_path)
    checkpoint_path = tmp_path / ".simflow" / "checkpoints" / "ckpt_001_analysis_visualization.json"
    payload = json.loads(checkpoint_path.read_text())
    payload["status"] = "failure"
    checkpoint_path.write_text(json.dumps(payload), encoding="utf-8")

    report = audit_state(str(tmp_path))
    assert any(
        item["rule_id"] == "checkpoint.registry_file_status_conflict"
        for item in report["audit_only_findings"]
    )
    apply_state_repair(str(tmp_path))
    registry = read_state(project_root=str(tmp_path), state_file="checkpoints.json")
    stages = read_state(project_root=str(tmp_path), state_file="stages.json")
    assert registry[0]["status"] == "completed"
    assert stages["analysis_visualization"].get("checkpoint_id") is None
    assert stages["analysis_visualization"].get("last_success_checkpoint_id") is None


def test_failure_checkpoint_is_tracked_separately(tmp_path):
    _fixture(tmp_path)
    registry = read_state(project_root=str(tmp_path), state_file="checkpoints.json")
    registry[0]["status"] = "failure"
    write_state(registry, project_root=str(tmp_path), state_file="checkpoints.json")
    checkpoint_path = tmp_path / registry[0]["path"]
    payload = json.loads(checkpoint_path.read_text())
    payload["status"] = "failure"
    checkpoint_path.write_text(json.dumps(payload), encoding="utf-8")

    apply_state_repair(str(tmp_path))
    stages = read_state(project_root=str(tmp_path), state_file="stages.json")
    stage = stages["analysis_visualization"]
    assert stage["failure_checkpoint_id"] == "ckpt_001_analysis_visualization"
    assert stage.get("checkpoint_id") is None
    assert stage.get("last_success_checkpoint_id") is None


def test_malformed_snapshot_is_not_recoverable(tmp_path):
    _fixture(tmp_path)
    checkpoint_path = tmp_path / ".simflow" / "checkpoints" / "ckpt_001_analysis_visualization.json"
    payload = json.loads(checkpoint_path.read_text())
    payload["state_snapshot"] = {"workflow.json": None, "stages.json": "bad"}
    checkpoint_path.write_text(json.dumps(payload), encoding="utf-8")

    apply_state_repair(str(tmp_path))
    registry = read_state(project_root=str(tmp_path), state_file="checkpoints.json")
    assert registry[0]["status"] == "partial"
    assert registry[0]["recoverable"] is False


def test_foreign_workflow_snapshot_is_not_recoverable(tmp_path):
    _fixture(tmp_path)
    checkpoint_path = tmp_path / ".simflow" / "checkpoints" / "ckpt_001_analysis_visualization.json"
    payload = json.loads(checkpoint_path.read_text())
    payload["state_snapshot"]["workflow.json"]["workflow_id"] = "wf_deadbeef"
    checkpoint_path.write_text(json.dumps(payload), encoding="utf-8")

    apply_state_repair(str(tmp_path))
    registry = read_state(project_root=str(tmp_path), state_file="checkpoints.json")
    stages = read_state(project_root=str(tmp_path), state_file="stages.json")
    assert registry[0]["status"] == "partial"
    assert registry[0]["recoverable"] is False
    assert stages["analysis_visualization"].get("last_success_checkpoint_id") is None


def test_repair_rejects_uninitialized_project(tmp_path):
    with pytest.raises(ValueError, match="initialized workflow"):
        audit_state(str(tmp_path))


def test_post_replace_failure_rolls_back_state(tmp_path, monkeypatch):
    from runtime.simflow_core import repair as repair_module

    _fixture(tmp_path)
    before = _tree_bytes(tmp_path)
    monkeypatch.setattr(
        repair_module,
        "_build_status_summary_md",
        lambda root: (_ for _ in ()).throw(OSError("injected report failure")),
    )

    with pytest.raises(OSError, match="injected report failure"):
        apply_state_repair(str(tmp_path))

    after = _tree_bytes(tmp_path)
    comparable_after = {
        name: content for name, content in after.items()
        if not name.startswith(".simflow/backups/")
    }
    assert comparable_after == before


def test_concurrent_change_during_backup_is_not_overwritten(tmp_path, monkeypatch):
    from runtime.simflow_core import repair as repair_module

    _fixture(tmp_path)
    real_backup = repair_module._backup_simflow_tree

    def backup_then_change(root):
        backup = real_backup(root)
        artifacts = read_state(project_root=str(tmp_path), state_file="artifacts.json")
        artifacts.append({
            "artifact_id": "art_87654321",
            "name": "concurrent.dat",
            "type": "output",
            "version": "v1.0.0",
            "stage": "computation",
            "path": None,
            "lineage": {"parent_artifacts": [], "parameters": {}, "software": None},
            "metadata": {},
            "checksum": None,
            "created_at": "2026-07-24T02:00:00+00:00",
        })
        write_state(artifacts, project_root=str(tmp_path), state_file="artifacts.json")
        return backup

    monkeypatch.setattr(repair_module, "_backup_simflow_tree", backup_then_change)
    with pytest.raises(RuntimeError, match="changed during repair backup"):
        apply_state_repair(str(tmp_path))

    artifacts = read_state(project_root=str(tmp_path), state_file="artifacts.json")
    assert any(item["artifact_id"] == "art_87654321" for item in artifacts)
