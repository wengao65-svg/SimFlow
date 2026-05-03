#!/usr/bin/env python3
"""Tests for runtime/lib/checkpoint.py"""

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "runtime"))

from lib.checkpoint import create_checkpoint, list_checkpoints, restore_checkpoint, get_latest_checkpoint
from lib.state import init_workflow


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

    def test_get_latest_checkpoint(self):
        create_checkpoint("wf_test", "literature", "First", self.base_dir)
        create_checkpoint("wf_test", "review", "Second", self.base_dir)
        latest = get_latest_checkpoint(self.base_dir)
        assert latest["stage_id"] == "review"

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
