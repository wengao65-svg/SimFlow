#!/usr/bin/env python3
"""Tests for bundled workflow-layer templates."""

import json
from pathlib import Path


TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "workflow" / "templates"
CANONICAL_STAGES = {"literature_review", "proposal", "modeling", "computation", "analysis_visualization", "writing"}
LEGACY_STAGE_NAMES = {"literature", "review", "input_generation", "compute", "analysis", "visualization"}


def _template_paths() -> list[Path]:
    return sorted(TEMPLATES_DIR.glob("*.json"))


def test_template_json_valid():
    for path in _template_paths():
        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict), f"Template {path.name} is not a JSON object"


def test_dry_run_templates_use_recipe_not_workflow_type():
    for path in sorted(TEMPLATES_DIR.glob("*_dry_run.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "recipe" in data
        assert "workflow_type" not in data


def test_dry_run_templates_use_canonical_stage_names():
    for path in sorted(TEMPLATES_DIR.glob("*_dry_run.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        stages = [stage["name"] for stage in data["stages"]]
        assert not LEGACY_STAGE_NAMES.intersection(stages), f"Template {path.name} uses legacy stages: {stages}"
        assert set(stages).issubset(CANONICAL_STAGES)


def test_stage_template_uses_open_guidance_fields():
    data = json.loads((TEMPLATES_DIR / "stage.template.json").read_text(encoding="utf-8"))
    assert data["name"] == "{{ stage_name }}"
    assert "intent" in data
    assert "evidence_outputs" in data
    assert "recommended_skills" in data
    for forbidden in ["default_agent", "default_skill", "required_inputs", "expected_outputs", "validators", "approval_gates"]:
        assert forbidden not in data
