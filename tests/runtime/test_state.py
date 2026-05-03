#!/usr/bin/env python3
"""Tests for runtime/lib/state.py"""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "runtime"))

from lib.state import (
    ensure_simflow_dir,
    init_workflow,
    read_state,
    write_state,
    update_stage,
)


class TestState:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.base_dir = self.tmpdir

    def teardown_method(self):
        shutil.rmtree(self.tmpdir)

    def test_ensure_simflow_dir(self):
        sf = ensure_simflow_dir(self.base_dir)
        assert sf.exists()
        assert (sf / "state").exists()
        assert (sf / "artifacts").exists()

    def test_init_workflow(self):
        state = init_workflow("dft", "literature", self.base_dir)
        assert state["workflow_id"].startswith("wf_")
        assert state["workflow_type"] == "dft"
        assert state["current_stage"] == "literature"
        assert state["status"] == "initialized"

    def test_read_write_state(self):
        data = {"test": True}
        write_state(data, self.base_dir, "test.json")
        result = read_state(self.base_dir, "test.json")
        assert result["test"] is True

    def test_update_stage(self):
        init_workflow("dft", "literature", self.base_dir)
        stage = update_stage("literature", "completed", self.base_dir)
        assert stage["status"] == "completed"
        assert stage["completed_at"] is not None

    def test_read_nonexistent_state(self):
        result = read_state(self.base_dir, "nonexistent.json")
        assert result == {}


if __name__ == "__main__":
    t = TestState()
    t.setup_method()
    try:
        t.test_ensure_simflow_dir()
        t.test_init_workflow()
        t.test_read_write_state()
        t.test_update_stage()
        t.test_read_nonexistent_state()
        print("All state tests passed!")
    finally:
        t.teardown_method()
