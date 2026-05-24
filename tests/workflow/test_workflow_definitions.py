#!/usr/bin/env python3
"""Tests for open workflow schema semantics."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = ROOT / "workflow" / "workflows"
WORKFLOW_SCHEMA = ROOT / "schemas" / "workflow.schema.json"


def test_legacy_workflow_examples_are_not_bundled():
    assert not list(WORKFLOWS_DIR.glob("*.json"))


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
