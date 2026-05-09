#!/usr/bin/env python3
"""Tests for simflow-handoff canonical registry behavior."""

import json
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "skills" / "simflow-handoff" / "scripts"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(ROOT))

from runtime.lib.state import init_workflow, read_state, write_state
from generate_handoff import generate_handoff


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


def _write_backbone_state(tmpdir: str):
    workflow = read_state(tmpdir, "workflow.json")
    workflow.update({
        "current_stage": "proposal",
        "status": "in_progress",
        "plan": "plans/workflow_plan.json",
        "stages": ["legacy_stage"],
        "stage_states": {"legacy_stage": "completed"},
    })
    write_state(workflow, project_root=tmpdir, state_file="workflow.json")
    write_state(
        {
            "workflow_id": workflow["workflow_id"],
            "workflow_type": "dft",
            "entry_point": "literature",
            "current_stage": "proposal",
            "stages": DFT_STAGES,
            "research_goal": "Study Si surface reconstruction",
            "material": "Si(001)",
            "software": "vasp",
        },
        project_root=tmpdir,
        state_file="metadata.json",
    )
    write_state(
        {
            "literature": {
                "stage_name": "literature",
                "status": "completed",
                "agent": None,
                "inputs": [],
                "outputs": [],
                "checkpoint_id": None,
                "error_message": None,
                "started_at": None,
                "completed_at": "2026-01-01T00:00:00+00:00",
            },
            "review": {
                "stage_name": "review",
                "status": "completed",
                "agent": None,
                "inputs": [],
                "outputs": [],
                "checkpoint_id": None,
                "error_message": None,
                "started_at": None,
                "completed_at": "2026-01-02T00:00:00+00:00",
            },
            "proposal": {
                "stage_name": "proposal",
                "status": "in_progress",
                "agent": None,
                "inputs": [],
                "outputs": [],
                "checkpoint_id": None,
                "error_message": None,
                "started_at": "2026-01-03T00:00:00+00:00",
                "completed_at": None,
            },
        },
        project_root=tmpdir,
        state_file="stages.json",
    )
    write_state(
        [
            {
                "artifact_id": "art_review01",
                "name": "review-notes",
                "type": "report",
                "version": "v1.0.0",
                "stage": "review",
                "path": "reports/review.json",
                "created_at": "2026-01-02T00:00:00+00:00",
            },
            {
                "artifact_id": "art_prop01",
                "name": "proposal-draft",
                "type": "plan",
                "version": "v1.0.0",
                "stage": "proposal",
                "path": "plans/proposal.md",
                "created_at": "2026-01-03T00:00:00+00:00",
            },
        ],
        project_root=tmpdir,
        state_file="artifacts.json",
    )
    write_state(
        [
            {
                "checkpoint_id": "ckpt_001_literature",
                "workflow_id": workflow["workflow_id"],
                "stage_id": "literature",
                "status": "success",
                "path": ".simflow/checkpoints/ckpt_001_literature.json",
                "created_at": "2026-01-01T00:00:00+00:00",
            },
            {
                "checkpoint_id": "ckpt_002_review",
                "workflow_id": workflow["workflow_id"],
                "stage_id": "review",
                "status": "success",
                "path": ".simflow/checkpoints/ckpt_002_review.json",
                "created_at": "2026-01-02T00:00:00+00:00",
            },
        ],
        project_root=tmpdir,
        state_file="checkpoints.json",
    )
    legacy_root = Path(tmpdir) / ".simflow"
    (legacy_root / "metadata.json").write_text(json.dumps({"workflow_type": "legacy"}, indent=2), encoding="utf-8")
    (legacy_root / "artifacts").mkdir(parents=True, exist_ok=True)
    (legacy_root / "artifacts" / "legacy.json").write_text(
        json.dumps({"artifact_id": "legacy_art", "stage": "legacy_stage"}, indent=2),
        encoding="utf-8",
    )


def test_generate_handoff_uses_canonical_registries():
    with tempfile.TemporaryDirectory() as tmpdir:
        init_workflow("dft", "literature", tmpdir)
        _write_backbone_state(tmpdir)

        result = generate_handoff(str(Path(tmpdir) / ".simflow"))
        handoff = result["handoff"]

        assert result["status"] == "success"
        assert handoff["current_stage"] == "proposal"
        assert handoff["completed_stages"] == ["literature", "review"]
        assert handoff["in_progress_stages"] == ["proposal"]
        assert handoff["pending_stages"] == ["modeling", "input_generation", "compute", "analysis", "visualization", "writing"]
        assert handoff["artifacts_count"] == 2
        assert handoff["latest_checkpoint"]["checkpoint_id"] == "ckpt_002_review"
        assert handoff["plan_reference"] == "plans/workflow_plan.json"
        assert "legacy_stage" not in handoff["completed_stages"]
        assert handoff["workflow_type"] == "dft"


def test_generate_handoff_writes_markdown_summary_with_backbone_fields():
    with tempfile.TemporaryDirectory() as tmpdir:
        init_workflow("dft", "literature", tmpdir)
        _write_backbone_state(tmpdir)
        output_path = Path(tmpdir) / ".simflow" / "reports" / "handoff.md"

        result = generate_handoff(str(Path(tmpdir) / ".simflow"), str(output_path))
        content = output_path.read_text(encoding="utf-8")

        assert result["status"] == "success"
        assert result["handoff"]["output_file"] == str(output_path)
        assert "Current stage: proposal" in content
        assert "Artifact count: 2" in content
        assert "Plan reference: plans/workflow_plan.json" in content
        assert "ckpt_002_review" in content


def test_generate_handoff_errors_without_workflow_state():
    with tempfile.TemporaryDirectory() as tmpdir:
        result = generate_handoff(str(Path(tmpdir) / ".simflow"))

        assert result["status"] == "error"
        assert result["message"] == "No workflow state found"
