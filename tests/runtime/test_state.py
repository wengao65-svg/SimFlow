#!/usr/bin/env python3
"""Tests for runtime/lib/state.py"""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "runtime"))

from lib.state import (
    ProjectRootError,
    ensure_simflow_dir,
    get_plugin_root,
    init_workflow,
    read_state,
    resolve_project_root,
    update_stage,
    write_state,
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
        assert (sf / "plans").exists()
        assert (sf / "artifacts").exists()
        assert (sf / "checkpoints").exists()
        assert (sf / "reports").exists()
        for path in [
            sf / "state" / "workflow.json",
            sf / "state" / "stages.json",
            sf / "state" / "artifacts.json",
            sf / "state" / "checkpoints.json",
            sf / "state" / "summary.json",
            sf / "state" / "metadata.json",
        ]:
            assert path.exists()
        assert not (sf / "metadata.json").exists()
        assert not (sf / "workflow_state.json").exists()

    def test_init_workflow(self):
        state = init_workflow("dft", "literature", self.base_dir)
        assert state["workflow_id"].startswith("wf_")
        assert state["workflow_type"] == "dft"
        assert state["current_stage"] == "literature"
        assert state["status"] == "initialized"
        sf = Path(self.base_dir) / ".simflow"
        for path in [
            sf / "state" / "workflow.json",
            sf / "state" / "stages.json",
            sf / "state" / "artifacts.json",
            sf / "state" / "checkpoints.json",
            sf / "state" / "summary.json",
            sf / "state" / "metadata.json",
            sf / "plans",
            sf / "artifacts",
            sf / "checkpoints",
            sf / "reports",
            sf / "logs",
        ]:
            assert path.exists()
        assert read_state(self.base_dir, "stages.json") == {}
        assert read_state(self.base_dir, "artifacts.json") == []
        assert read_state(self.base_dir, "checkpoints.json") == []
        assert read_state(self.base_dir, "metadata.json") == {}
        summary = read_state(self.base_dir, "summary.json")
        assert summary["state_root"] == ".simflow"
        assert (sf / "reports" / "status_summary.md").is_file()
        assert not (sf / "metadata.json").exists()
        assert not (sf / "workflow_state.json").exists()

    def test_init_workflow_ignores_existing_omx_state(self):
        omx = Path(self.base_dir) / ".omx"
        omx.mkdir()
        host_summary = omx / "simflow_status_summary.md"
        host_summary.write_text("host session summary\n", encoding="utf-8")
        host_state = omx / "session.json"
        host_state.write_text('{"owner":"oh-my-codex"}\n', encoding="utf-8")

        init_workflow("custom", "literature", self.base_dir)

        assert (Path(self.base_dir) / ".simflow" / "state" / "workflow.json").is_file()
        assert (Path(self.base_dir) / ".simflow" / "reports" / "status_summary.md").is_file()
        assert host_summary.read_text(encoding="utf-8") == "host session summary\n"
        assert host_state.read_text(encoding="utf-8") == '{"owner":"oh-my-codex"}\n'

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

    def test_resolve_project_root_rejects_plugin_root(self):
        with pytest.raises(ProjectRootError):
            resolve_project_root(project_root=str(get_plugin_root()))

    def test_resolve_project_root_rejects_plugin_cache_shape(self):
        fake_plugin_root = Path(self.base_dir) / "simflow-cache"
        (fake_plugin_root / ".codex-plugin").mkdir(parents=True)
        (fake_plugin_root / "skills" / "simflow").mkdir(parents=True)
        (fake_plugin_root / "runtime" / "lib").mkdir(parents=True)
        (fake_plugin_root / ".codex-plugin" / "plugin.json").write_text("{}", encoding="utf-8")
        (fake_plugin_root / "skills" / "simflow" / "SKILL.md").write_text("# SimFlow\n", encoding="utf-8")
        (fake_plugin_root / "runtime" / "lib" / "state.py").write_text("# marker\n", encoding="utf-8")

        with pytest.raises(ProjectRootError):
            resolve_project_root(project_root=str(fake_plugin_root))


if __name__ == "__main__":
    t = TestState()
    t.setup_method()
    try:
        t.test_ensure_simflow_dir()
        t.test_init_workflow()
        t.test_init_workflow_ignores_existing_omx_state()
        t.test_read_write_state()
        t.test_update_stage()
        t.test_read_nonexistent_state()
        print("All state tests passed!")
    finally:
        t.teardown_method()
