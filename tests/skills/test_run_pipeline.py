#!/usr/bin/env python3
"""Tests for simflow-pipeline canonical state behavior."""

import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "skills" / "simflow-pipeline" / "scripts"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(ROOT))

from runtime.lib.state import init_workflow, read_state, write_state
from run_pipeline import run_pipeline


DFT_STAGES = [
    "literature",
    "review",
    "proposal",
    "modeling",
    "input_generation",
    "compute",
    "analysis",
    "visualization",
    "writing",
]


def _write_metadata(tmpdir: str):
    state = read_state(tmpdir, "workflow.json")
    metadata = {
        "workflow_id": state["workflow_id"],
        "workflow_type": "dft",
        "entry_point": "literature",
        "current_stage": "literature",
        "research_goal": "Study Si surface reconstruction",
        "material": "Si(001)",
        "software": "vasp",
        "parameters": {},
        "stages": DFT_STAGES,
    }
    write_state(metadata, project_root=tmpdir, state_file="metadata.json")


def test_run_pipeline_dry_run_uses_canonical_stage_sequence():
    with tempfile.TemporaryDirectory() as tmpdir:
        init_workflow("dft", "literature", tmpdir)
        _write_metadata(tmpdir)
        workflow = read_state(tmpdir, "workflow.json")
        workflow["stages"] = ["legacy_stage"]
        write_state(workflow, project_root=tmpdir, state_file="workflow.json")

        result = run_pipeline(str(Path(tmpdir) / ".simflow"), target_stage="proposal", dry_run=True)
        stages_state = read_state(tmpdir, "stages.json")

        assert result["status"] == "success"
        assert [item["stage"] for item in result["results"]] == ["literature", "review", "proposal"]
        assert all(item["status"] == "dry_run_complete" for item in result["results"])
        assert stages_state["literature"]["status"] == "pending"
        assert stages_state["review"]["status"] == "pending"
        assert stages_state["proposal"]["status"] == "pending"
        assert "legacy_stage" not in stages_state
        assert not (Path(tmpdir) / ".simflow" / "workflow_state.json").exists()


def test_run_pipeline_execute_updates_stages_and_checkpoint_registry():
    with tempfile.TemporaryDirectory() as tmpdir:
        init_workflow("dft", "literature", tmpdir)
        _write_metadata(tmpdir)

        result = run_pipeline(str(Path(tmpdir) / ".simflow"), target_stage="review", dry_run=False)
        workflow = read_state(tmpdir, "workflow.json")
        stages_state = read_state(tmpdir, "stages.json")
        checkpoints = read_state(tmpdir, "checkpoints.json")

        assert result["status"] == "success"
        assert [item["stage"] for item in result["results"]] == ["literature", "review"]
        assert all(item["status"] == "completed" for item in result["results"])
        assert workflow["current_stage"] == "review"
        assert workflow["status"] == "in_progress"
        assert stages_state["literature"]["status"] == "completed"
        assert stages_state["review"]["status"] == "completed"
        assert stages_state["review"]["checkpoint_id"] == result["checkpoint_id"]
        assert len(checkpoints) == 1
        assert checkpoints[0]["checkpoint_id"] == result["checkpoint_id"]
        assert checkpoints[0]["stage_id"] == "review"
        assert not (Path(tmpdir) / ".simflow" / "workflow_state.json").exists()
        assert not (Path(tmpdir) / ".simflow" / "metadata.json").exists()


def test_run_pipeline_execute_starts_after_completed_current_stage():
    with tempfile.TemporaryDirectory() as tmpdir:
        init_workflow("dft", "literature", tmpdir)
        _write_metadata(tmpdir)
        workflow = read_state(tmpdir, "workflow.json")
        workflow["current_stage"] = "review"
        write_state(workflow, project_root=tmpdir, state_file="workflow.json")
        write_state(
            {
                "review": {
                    "stage_name": "review",
                    "status": "completed",
                    "agent": None,
                    "inputs": [],
                    "outputs": [],
                    "checkpoint_id": None,
                    "error_message": None,
                    "started_at": None,
                    "completed_at": "2026-01-01T00:00:00+00:00",
                }
            },
            project_root=tmpdir,
            state_file="stages.json",
        )

        result = run_pipeline(str(Path(tmpdir) / ".simflow"), target_stage="modeling", dry_run=False)

        assert [item["stage"] for item in result["results"]] == ["proposal", "modeling"]
