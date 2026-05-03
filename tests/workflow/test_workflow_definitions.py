#!/usr/bin/env python3
"""Tests for workflow definitions (dft.json, aimd.json, md.json)."""

import json
from pathlib import Path

WORKFLOWS_DIR = Path(__file__).resolve().parents[2] / "workflow" / "workflows"

EXPECTED_WORKFLOWS = ["dft", "aimd", "md"]


def test_all_workflows_exist():
    for name in EXPECTED_WORKFLOWS:
        path = WORKFLOWS_DIR / f"{name}.json"
        assert path.exists(), f"Missing workflow: {name}"


def test_workflow_json_valid():
    for name in EXPECTED_WORKFLOWS:
        path = WORKFLOWS_DIR / f"{name}.json"
        data = json.loads(path.read_text())
        assert isinstance(data, dict)


def test_workflow_has_required_fields():
    for name in EXPECTED_WORKFLOWS:
        path = WORKFLOWS_DIR / f"{name}.json"
        data = json.loads(path.read_text())
        assert "name" in data or "workflow_name" in data, f"{name} missing name"
        assert "stages" in data, f"{name} missing stages"


def test_workflow_stages_is_array():
    for name in EXPECTED_WORKFLOWS:
        path = WORKFLOWS_DIR / f"{name}.json"
        data = json.loads(path.read_text())
        assert isinstance(data["stages"], list), f"{name} stages not a list"
        assert len(data["stages"]) > 0, f"{name} has no stages"


def test_workflow_type_matches():
    for name in EXPECTED_WORKFLOWS:
        path = WORKFLOWS_DIR / f"{name}.json"
        data = json.loads(path.read_text())
        wf_name = data.get("workflow_name") or data.get("name", "")
        assert name in wf_name.lower(), f"{name} name mismatch: {wf_name}"


def test_workflow_stages_have_names():
    for name in EXPECTED_WORKFLOWS:
        path = WORKFLOWS_DIR / f"{name}.json"
        data = json.loads(path.read_text())
        for stage in data["stages"]:
            if isinstance(stage, dict):
                assert "name" in stage, f"{name} stage missing name"
            else:
                assert isinstance(stage, str), f"{name} stage is not string or dict"


def test_workflow_stage_dependencies_valid():
    for name in EXPECTED_WORKFLOWS:
        path = WORKFLOWS_DIR / f"{name}.json"
        data = json.loads(path.read_text())
        stage_names = set()
        for s in data["stages"]:
            stage_names.add(s["name"] if isinstance(s, dict) else s)
        deps = data.get("stage_dependencies", {})
        for stage, dep_list in deps.items():
            for dep in dep_list:
                assert dep in stage_names, f"{name}: {stage} depends on unknown {dep}"


def test_workflow_has_entry_point():
    for name in EXPECTED_WORKFLOWS:
        path = WORKFLOWS_DIR / f"{name}.json"
        data = json.loads(path.read_text())
        has_entry = ("entry_point" in data or "entry_points" in data
                     or "default_entry" in data)
        assert has_entry, f"{name} missing entry_point"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        print(f"  {t.__name__}...", end=" ")
        t()
        print("OK")
    print(f"\n  All {len(tests)} tests passed!")
