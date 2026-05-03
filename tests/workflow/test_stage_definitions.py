#!/usr/bin/env python3
"""Tests for workflow stage definitions."""

import json
from pathlib import Path

STAGES_DIR = Path(__file__).resolve().parents[2] / "workflow" / "stages"

REQUIRED_STAGES = [
    "literature", "review", "proposal", "modeling",
    "input_generation", "compute", "analysis", "visualization", "writing",
]


def test_all_stages_exist():
    for name in REQUIRED_STAGES:
        path = STAGES_DIR / f"{name}.json"
        assert path.exists(), f"Missing stage: {name}"


def test_stage_json_valid():
    for name in REQUIRED_STAGES:
        path = STAGES_DIR / f"{name}.json"
        data = json.loads(path.read_text())
        assert isinstance(data, dict), f"Stage {name} is not a dict"


def test_stage_has_required_fields():
    for name in REQUIRED_STAGES:
        path = STAGES_DIR / f"{name}.json"
        data = json.loads(path.read_text())
        assert "name" in data, f"Stage {name} missing 'name'"
        assert "description" in data, f"Stage {name} missing 'description'"
        assert "default_skill" in data or "skill" in data, f"Stage {name} missing skill"


def test_stage_name_matches_filename():
    for name in REQUIRED_STAGES:
        path = STAGES_DIR / f"{name}.json"
        data = json.loads(path.read_text())
        assert data["name"] == name, f"Stage {name} name mismatch: {data.get('name')}"


def test_stage_has_skill():
    for name in REQUIRED_STAGES:
        path = STAGES_DIR / f"{name}.json"
        data = json.loads(path.read_text())
        assert "default_skill" in data or "skill" in data, f"Stage {name} missing skill"


def test_stage_has_inputs_outputs():
    for name in REQUIRED_STAGES:
        path = STAGES_DIR / f"{name}.json"
        data = json.loads(path.read_text())
        inputs = data.get("inputs") or data.get("required_inputs") or []
        outputs = data.get("outputs") or data.get("expected_outputs") or []
        assert isinstance(inputs, list), f"Stage {name} inputs not a list"
        assert isinstance(outputs, list), f"Stage {name} outputs not a list"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        print(f"  {t.__name__}...", end=" ")
        t()
        print("OK")
    print(f"\n  All {len(tests)} tests passed!")
