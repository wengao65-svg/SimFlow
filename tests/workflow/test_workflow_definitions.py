#!/usr/bin/env python3
"""Tests for workflow definitions and open workflow schema semantics."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = ROOT / "workflow" / "workflows"
WORKFLOW_SCHEMA = ROOT / "schemas" / "workflow.schema.json"

EXPECTED_LEGACY_WORKFLOWS = ["dft", "aimd", "md"]


def _load_workflow(name: str) -> dict:
    return json.loads((WORKFLOWS_DIR / f"{name}.json").read_text())


def test_legacy_workflow_examples_remain_available():
    for name in EXPECTED_LEGACY_WORKFLOWS:
        path = WORKFLOWS_DIR / f"{name}.json"
        assert path.exists(), f"Missing workflow example: {name}"


def test_workflow_json_valid():
    for path in sorted(WORKFLOWS_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        assert isinstance(data, dict)


def test_workflow_has_required_fields():
    for path in sorted(WORKFLOWS_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        assert "name" in data or "workflow_name" in data, f"{path.name} missing name"
        assert "stages" in data, f"{path.name} missing stages"


def test_workflow_stages_is_array():
    for path in sorted(WORKFLOWS_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        assert isinstance(data["stages"], list), f"{path.name} stages not a list"
        assert len(data["stages"]) > 0, f"{path.name} has no stages"


def test_workflow_stages_have_names_or_string_ids():
    for path in sorted(WORKFLOWS_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        for stage in data["stages"]:
            if isinstance(stage, dict):
                assert "name" in stage, f"{path.name} stage missing name"
            else:
                assert isinstance(stage, str), f"{path.name} stage is not string or dict"


def test_workflow_stage_dependencies_valid():
    for path in sorted(WORKFLOWS_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        stage_names = {stage["name"] if isinstance(stage, dict) else stage for stage in data["stages"]}
        deps = data.get("stage_dependencies", {})
        for stage, dep_list in deps.items():
            assert stage in stage_names, f"{path.name}: dependency key {stage} is not a stage"
            for dep in dep_list:
                assert dep in stage_names, f"{path.name}: {stage} depends on unknown {dep}"


def test_workflow_has_independent_entry_information():
    for path in sorted(WORKFLOWS_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        has_entry = "entry_point" in data or "entry_points" in data or "default_entry" in data
        assert has_entry, f"{path.name} missing entry metadata"


def test_workflow_schema_has_open_type_and_software_contracts():
    schema = json.loads(WORKFLOW_SCHEMA.read_text())
    workflow_type = schema["properties"]["workflow_type"]
    assert "enum" not in workflow_type
    assert "recipe" in schema["properties"]
    assert "tags" in schema["properties"]
    assert "software" in schema["properties"]


def test_workflow_schema_allows_string_or_object_stages():
    schema = json.loads(WORKFLOW_SCHEMA.read_text())
    stage_items = schema["properties"]["stages"]["items"]["oneOf"]
    stage_types = {item.get("type") for item in stage_items}
    assert {"string", "object"}.issubset(stage_types)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        print(f"  {t.__name__}...", end=" ")
        t()
        print("OK")
    print(f"\n  All {len(tests)} tests passed!")
