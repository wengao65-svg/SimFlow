#!/usr/bin/env python3
"""Tests for workflow stage definitions."""

import json
from pathlib import Path

STAGES_DIR = Path(__file__).resolve().parents[2] / "workflow" / "stages"

REQUIRED_STAGES = [
    "literature", "review", "proposal", "modeling",
    "input_generation", "compute", "analysis", "visualization", "writing",
]


MILESTONE_C_STAGE_EXPECTATIONS = {
    "modeling": {
        "required_inputs": ["proposal.md", "parameter_table.csv", "research_questions.json"],
        "expected_outputs": ["structure_manifest.json", "structure_file", "modeling_report.md"],
        "artifact_types": ["structure_manifest", "structure", "modeling_report"],
    },
    "compute": {
        "required_inputs": ["input_manifest.json"],
        "expected_outputs": ["compute_plan.json", "job_script.sh", "dry_run_report.json"],
        "artifact_types": ["compute_plan", "job_script", "dry_run_report"],
    },
    "analysis": {
        "required_inputs": ["compute_plan.json"],
        "expected_outputs": ["analysis_report.json", "analysis_report.md"],
        "artifact_types": ["analysis_report", "analysis_markdown"],
    },
    "visualization": {
        "required_inputs": ["analysis_report.json"],
        "expected_outputs": ["figures", "figures_manifest.json"],
        "artifact_types": ["figure", "figures_manifest"],
    },
}


def _load_stage(name: str) -> dict:
    return json.loads((STAGES_DIR / f"{name}.json").read_text())


def test_all_stages_exist():
    for name in REQUIRED_STAGES:
        path = STAGES_DIR / f"{name}.json"
        assert path.exists(), f"Missing stage: {name}"


def test_stage_json_valid():
    for name in REQUIRED_STAGES:
        data = _load_stage(name)
        assert isinstance(data, dict), f"Stage {name} is not a dict"


def test_stage_has_required_fields():
    for name in REQUIRED_STAGES:
        data = _load_stage(name)
        assert "name" in data, f"Stage {name} missing 'name'"
        assert "description" in data, f"Stage {name} missing 'description'"
        assert "default_skill" in data or "skill" in data, f"Stage {name} missing skill"


def test_stage_name_matches_filename():
    for name in REQUIRED_STAGES:
        data = _load_stage(name)
        assert data["name"] == name, f"Stage {name} name mismatch: {data.get('name')}"


def test_stage_has_skill():
    for name in REQUIRED_STAGES:
        data = _load_stage(name)
        assert "default_skill" in data or "skill" in data, f"Stage {name} missing skill"


def test_stage_has_inputs_outputs():
    for name in REQUIRED_STAGES:
        data = _load_stage(name)
        inputs = data.get("inputs") or data.get("required_inputs") or []
        outputs = data.get("outputs") or data.get("expected_outputs") or []
        assert isinstance(inputs, list), f"Stage {name} inputs not a list"
        assert isinstance(outputs, list), f"Stage {name} outputs not a list"


def test_milestone_c_stage_contracts_are_aligned():
    for name, expected in MILESTONE_C_STAGE_EXPECTATIONS.items():
        data = _load_stage(name)
        assert data.get("required_inputs") == expected["required_inputs"]
        assert data.get("expected_outputs") == expected["expected_outputs"]
        assert data.get("artifact_types") == expected["artifact_types"]


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        print(f"  {t.__name__}...", end=" ")
        t()
        print("OK")
    print(f"\n  All {len(tests)} tests passed!")
