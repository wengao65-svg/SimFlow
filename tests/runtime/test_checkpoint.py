#!/usr/bin/env python3
"""Tests for runtime/lib/checkpoint.py"""

import json
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "runtime"))

import runtime.simflow_core.checkpoints as checkpoint_module
from runtime.simflow_core.checkpoints import create_checkpoint, list_checkpoints, restore_checkpoint, get_latest_checkpoint
from runtime.simflow_core.artifacts import register_artifact
from runtime.simflow_core.state import init_workflow, read_state, update_stage


class TestCheckpoint:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.base_dir = self.tmpdir
        init_workflow("dft", "literature", self.base_dir)

    def teardown_method(self):
        shutil.rmtree(self.tmpdir)

    def test_create_checkpoint(self):
        ckpt = create_checkpoint("wf_test1234", "literature", "After literature", self.base_dir)
        assert ckpt["checkpoint_id"].startswith("ckpt_")
        assert ckpt["workflow_id"] == "wf_test1234"
        assert ckpt["status"] == "success"
        assert "lineage_snapshot" in ckpt
        assert ckpt["simflow_result"]["role"] == "state_admin"
        assert ckpt["simflow_result"]["activity"] == "create_checkpoint"
        assert ckpt["simflow_result"]["state_effect"] == "checkpoint_admin"
        registry_path = Path(self.base_dir) / ".simflow" / "state" / "checkpoints.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        assert registry[0]["checkpoint_id"] == ckpt["checkpoint_id"]

    def test_checkpoint_captures_lineage_snapshot(self):
        parent = register_artifact("input.json", "input_manifest", "computation", self.base_dir)
        child = register_artifact(
            "analysis.json",
            "custom_analysis",
            "analysis_visualization",
            self.base_dir,
            parent_artifacts=[parent["artifact_id"]],
        )

        ckpt = create_checkpoint("wf_test", "analysis_visualization", "After analysis", self.base_dir)
        links = ckpt["lineage_snapshot"]["links"]
        assert any(
            link["parent_artifact_id"] == parent["artifact_id"]
            and link["child_artifact_id"] == child["artifact_id"]
            for link in links
        )

    def test_list_checkpoints(self):
        create_checkpoint("wf_test", "literature", "First", self.base_dir)
        create_checkpoint("wf_test", "review", "Second", self.base_dir)
        ckpts = list_checkpoints(self.base_dir)
        assert len(ckpts) == 2

    def test_restore_checkpoint(self):
        create_checkpoint("wf_test", "literature", "Save point", self.base_dir)
        ckpts = list_checkpoints(self.base_dir)
        restored = restore_checkpoint(ckpts[0]["checkpoint_id"], self.base_dir)
        assert restored["checkpoint_id"] == ckpts[0]["checkpoint_id"]
        assert restored["simflow_result"]["activity"] == "restore_checkpoint"

    def test_get_latest_checkpoint(self):
        create_checkpoint("wf_test", "literature", "First", self.base_dir)
        create_checkpoint("wf_test", "review", "Second", self.base_dir)
        latest = get_latest_checkpoint(self.base_dir)
        assert latest["stage_id"] == "review"

    def test_create_checkpoint_rejects_noncanonical_status(self):
        with pytest.raises(ValueError):
            create_checkpoint("wf_test1234", "literature", "After literature", self.base_dir, status="warning")

    def test_create_checkpoint_snapshots_stage_state_with_own_checkpoint_id(self):
        update_stage(
            "modeling",
            "completed",
            self.base_dir,
            inputs=["art_input"],
            outputs=["art_output"],
        )

        ckpt = create_checkpoint("wf_test1234", "modeling", "After modeling", self.base_dir)

        stage_snapshot = ckpt["state_snapshot"]["stages.json"]["modeling"]
        checkpoint_registry = ckpt["state_snapshot"]["checkpoints.json"]

        assert stage_snapshot["status"] == "completed"
        assert stage_snapshot["inputs"] == ["art_input"]
        assert stage_snapshot["outputs"] == ["art_output"]
        assert stage_snapshot["checkpoint_id"] == ckpt["checkpoint_id"]
        assert checkpoint_registry[-1]["checkpoint_id"] == ckpt["checkpoint_id"]

    def test_restore_checkpoint_uses_active_registry_view_without_deleting_artifact_payloads(self):
        payload = Path(self.base_dir) / ".simflow" / "artifacts" / "modeling" / "POSCAR"
        payload.parent.mkdir(parents=True, exist_ok=True)
        payload.write_text("Si\n", encoding="utf-8")
        register_artifact("POSCAR", "structure", "modeling", self.base_dir, path=".simflow/artifacts/modeling/POSCAR")

        update_stage("modeling", "completed", self.base_dir, outputs=["art_model"])
        ckpt1 = create_checkpoint("wf_test1234", "modeling", "After modeling", self.base_dir)

        update_stage("computation", "completed", self.base_dir, inputs=["art_model"], outputs=["art_compute"])
        ckpt2 = create_checkpoint("wf_test1234", "computation", "After computation", self.base_dir)

        restored = restore_checkpoint(ckpt1["checkpoint_id"], self.base_dir)
        registry = read_state(self.base_dir, "checkpoints.json")
        listed = list_checkpoints(self.base_dir)

        assert restored["checkpoint_id"] == ckpt1["checkpoint_id"]
        assert [entry["checkpoint_id"] for entry in registry] == [ckpt1["checkpoint_id"]]
        assert [entry["checkpoint_id"] for entry in listed] == [ckpt1["checkpoint_id"]]
        assert (Path(self.base_dir) / ".simflow" / "checkpoints" / f"{ckpt2['checkpoint_id']}.json").is_file()
        assert payload.is_file()

    def test_restore_checkpoint_removes_future_only_state_files(self):
        update_stage("modeling", "completed", self.base_dir, outputs=["art_model"])
        checkpoint = create_checkpoint("wf_test1234", "modeling", "After modeling", self.base_dir)

        future_only = Path(self.base_dir) / ".simflow" / "state" / "future_only.json"
        future_only.write_text('{"future": true}\n', encoding="utf-8")

        restore_checkpoint(checkpoint["checkpoint_id"], self.base_dir)

        assert not future_only.exists()

    def test_restore_checkpoint_rolls_back_all_state_bytes_on_replace_failure(self, monkeypatch):
        update_stage("modeling", "completed", self.base_dir, outputs=["art_model"])
        checkpoint = create_checkpoint("wf_test1234", "modeling", "After modeling", self.base_dir)

        artifact_payload = Path(self.base_dir) / ".simflow" / "artifacts" / "modeling" / "POSCAR"
        artifact_payload.parent.mkdir(parents=True, exist_ok=True)
        artifact_payload.write_text("Si\n", encoding="utf-8")

        update_stage("computation", "completed", self.base_dir, outputs=["art_compute"])
        future_only = Path(self.base_dir) / ".simflow" / "state" / "future_only.json"
        future_only.write_text('{"future": true}\n', encoding="utf-8")
        state_dir = Path(self.base_dir) / ".simflow" / "state"
        pre_restore_bytes = {
            path.name: path.read_bytes()
            for path in sorted(state_dir.glob("*.json"))
        }
        original_replace = checkpoint_module._ORIGINAL_OS_REPLACE

        def flaky_replace(src, dst):
            if Path(dst).name == "workflow.json":
                raise OSError("injected workflow.json replace failure")
            return original_replace(src, dst)

        monkeypatch.setattr(checkpoint_module, "_ORIGINAL_OS_REPLACE", flaky_replace)

        with pytest.raises(OSError, match="injected workflow.json replace failure"):
            restore_checkpoint(checkpoint["checkpoint_id"], self.base_dir)

        post_restore_bytes = {
            path.name: path.read_bytes()
            for path in sorted(state_dir.glob("*.json"))
        }
        assert post_restore_bytes == pre_restore_bytes
        assert artifact_payload.read_text(encoding="utf-8") == "Si\n"

    def test_create_checkpoint_rolls_back_state_and_file_on_registry_write_failure(self, monkeypatch):
        update_stage("modeling", "completed", self.base_dir, outputs=["art_model"])
        original_stage = read_state(self.base_dir, "stages.json")
        original_registry = read_state(self.base_dir, "checkpoints.json")
        original_replace = checkpoint_module.os.replace

        def flaky_replace(src, dst):
            if Path(dst).name == "checkpoints.json":
                raise OSError("injected checkpoints.json replace failure")
            return original_replace(src, dst)

        monkeypatch.setattr(checkpoint_module.os, "replace", flaky_replace)

        with pytest.raises(OSError, match="injected checkpoints.json replace failure"):
            create_checkpoint("wf_test1234", "modeling", "After modeling", self.base_dir)

        checkpoint_files = list((Path(self.base_dir) / ".simflow" / "checkpoints").glob("ckpt_*.json"))
        assert checkpoint_files == []
        assert read_state(self.base_dir, "stages.json") == original_stage
        assert read_state(self.base_dir, "checkpoints.json") == original_registry

    def test_restore_nonexistent(self):
        try:
            restore_checkpoint("ckpt_nonexistent", self.base_dir)
            assert False, "Should have raised"
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    methods = ["test_create_checkpoint", "test_list_checkpoints", "test_restore_checkpoint", "test_get_latest_checkpoint", "test_restore_nonexistent"]
    for method in methods:
        t = TestCheckpoint()
        t.setup_method()
        try:
            getattr(t, method)()
            print(f"  PASS: {method}")
        except Exception as e:
            print(f"  FAIL: {method} - {e}")
        finally:
            t.teardown_method()
    print("All checkpoint tests passed!")
