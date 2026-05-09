#!/usr/bin/env python3
"""Tests for simflow-stage canonical state behavior."""

import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "skills" / "simflow-stage" / "scripts"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(ROOT))

from runtime.lib.state import init_workflow, read_state, write_state
from execute_stage import execute_stage


def _write_metadata(tmpdir: str, workflow_type: str = "dft"):
    state = read_state(tmpdir, "workflow.json")
    metadata = {
        "workflow_id": state["workflow_id"],
        "workflow_type": workflow_type,
        "entry_point": "literature" if workflow_type == "dft" else "proposal",
        "current_stage": "literature" if workflow_type == "dft" else "proposal",
        "stages": [],
    }
    write_state(metadata, project_root=tmpdir, state_file="metadata.json")


def test_execute_stage_dry_run_uses_workflow_definition_not_workflow_json_stages():
    with tempfile.TemporaryDirectory() as tmpdir:
        init_workflow("dft", "literature", tmpdir)
        _write_metadata(tmpdir, "dft")
        workflow = read_state(tmpdir, "workflow.json")
        workflow["stages"] = ["legacy_stage"]
        write_state(workflow, project_root=tmpdir, state_file="workflow.json")

        result = execute_stage(str(Path(tmpdir) / ".simflow"), "review", dry_run=True)
        stages_state = read_state(tmpdir, "stages.json")

        assert result["status"] == "dry_run_complete"
        assert result["stage"] == "review"
        assert stages_state["review"]["status"] == "pending"
        assert "legacy_stage" not in stages_state
        assert not (Path(tmpdir) / ".simflow" / "workflow_state.json").exists()


def test_execute_stage_rejects_stage_not_in_workflow_definition():
    with tempfile.TemporaryDirectory() as tmpdir:
        init_workflow("aimd", "proposal", tmpdir)
        _write_metadata(tmpdir, "aimd")

        result = execute_stage(str(Path(tmpdir) / ".simflow"), "literature", dry_run=True)
        stages_state = read_state(tmpdir, "stages.json")

        assert result["status"] == "error"
        assert result["message"] == "Unknown stage: literature"
        assert stages_state == {}


def test_execute_stage_execute_updates_canonical_stages_state():
    with tempfile.TemporaryDirectory() as tmpdir:
        init_workflow("dft", "literature", tmpdir)
        _write_metadata(tmpdir, "dft")

        result = execute_stage(str(Path(tmpdir) / ".simflow"), "modeling", params={"supercell": "2x2x1"}, dry_run=False)
        stages_state = read_state(tmpdir, "stages.json")

        assert result["status"] == "completed"
        assert result["params"] == {"supercell": "2x2x1"}
        assert stages_state["modeling"]["status"] == "completed"
        assert any(script["status"] == "available" for script in result["scripts"])
        assert not (Path(tmpdir) / ".simflow" / "workflow_state.json").exists()
        assert not (Path(tmpdir) / ".simflow" / "metadata.json").exists()
