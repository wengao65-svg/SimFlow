#!/usr/bin/env python3
"""Tests for legacy SimFlow migration helpers."""

import json
from pathlib import Path

from runtime.lib.migration import (
    convert_workflow_file,
    inspect_legacy_project,
    migrate_project_state,
)


def _write_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_inspect_legacy_project_detects_stage_mapping(tmp_path):
    simflow = tmp_path / ".simflow"
    _write_json(simflow / "metadata.json", {"workflow_type": "md", "current_stage": "compute"})
    _write_json(
        simflow / "workflow_state.json",
        {"workflow_id": "wf_legacy", "workflow_type": "md", "current_stage": "input_generation"},
    )

    result = inspect_legacy_project(str(tmp_path))

    assert result["legacy_detected"] is True
    assert result["workflow_type"] == "md"
    assert result["recipe"] == "classical_md"
    assert result["canonical_current_stage"] == "computation"
    assert ".simflow/metadata.json" in result["legacy_files"]
    assert result["stage_map"]["input_generation"] == "computation"


def test_migrate_project_state_preserves_legacy_files_and_writes_canonical_state(tmp_path):
    simflow = tmp_path / ".simflow"
    _write_json(
        simflow / "workflow_state.json",
        {
            "workflow_id": "wf_legacy",
            "workflow_type": "dft",
            "current_stage": "input_generation",
            "stages": ["literature", "review", "proposal", "input_generation", "compute", "analysis"],
            "stage_states": {
                "literature": "completed",
                "review": "completed",
                "input_generation": "completed",
                "compute": "in_progress",
            },
        },
    )
    _write_json(simflow / "metadata.json", {"workflow_type": "dft"})
    legacy_report = simflow / "review_summary.md"
    legacy_report.write_text("legacy review\n", encoding="utf-8")
    _write_json(
        simflow / "artifacts" / "legacy_artifact.json",
        {"artifact_id": "art_legacy", "name": "legacy", "stage": "input_generation"},
    )
    _write_json(
        simflow / "checkpoints" / "legacy_checkpoint.json",
        {"checkpoint_id": "ckpt_legacy", "stage": "compute"},
    )

    result = migrate_project_state(str(tmp_path))

    assert result["status"] == "success"
    assert result["recipe"] == "dft"
    assert result["current_stage"] == "computation"
    assert (simflow / "workflow_state.json").is_file()
    assert (simflow / "metadata.json").is_file()

    workflow = json.loads((simflow / "state" / "workflow.json").read_text(encoding="utf-8"))
    assert workflow["workflow_id"] == "wf_legacy"
    assert workflow["workflow_type"] == "custom"
    assert workflow["recipe"] == "dft"
    assert workflow["legacy_workflow_type"] == "dft"
    assert workflow["current_stage"] == "computation"

    stages = json.loads((simflow / "state" / "stages.json").read_text(encoding="utf-8"))
    assert "input_generation" not in stages
    assert stages["literature_review"]["status"] == "completed"
    assert set(stages["computation"]["legacy_stages"]) == {"input_generation", "compute"}

    artifacts = json.loads((simflow / "state" / "artifacts.json").read_text(encoding="utf-8"))
    assert artifacts[0]["stage"] == "computation"
    assert artifacts[0]["legacy_stage"] == "input_generation"

    checkpoints = json.loads((simflow / "state" / "checkpoints.json").read_text(encoding="utf-8"))
    assert checkpoints[0]["stage"] == "computation"
    assert checkpoints[0]["legacy_stage"] == "compute"

    assert (simflow / "reports" / "migration.json").is_file()
    assert (simflow / "reports" / "migration.md").is_file()
    assert (simflow / "reports" / "legacy" / "review_summary.md").read_text(encoding="utf-8") == "legacy review\n"


def test_convert_workflow_file_writes_open_recipe(tmp_path):
    workflow_path = tmp_path / "md.json"
    output_path = tmp_path / "md.recipe.json"
    _write_json(
        workflow_path,
        {
            "name": "md",
            "description": "Legacy MD workflow",
            "stages": ["proposal", "modeling", "input_generation", "compute", "analysis", "visualization"],
            "stage_dependencies": {"compute": ["input_generation"]},
            "default_entry": "proposal",
        },
    )

    recipe = convert_workflow_file(str(workflow_path), str(output_path))
    saved = json.loads(output_path.read_text(encoding="utf-8"))

    assert recipe["recipe_type"] == "classical_md"
    assert recipe["stages"] == ["proposal", "modeling", "computation", "analysis_visualization"]
    assert recipe["legacy_stage_dependencies"] == {"compute": ["input_generation"]}
    assert saved == recipe
