#!/usr/bin/env python3
"""Tests for open workflow stage definitions."""

import json
from pathlib import Path

from runtime.simflow_core.validation import load_stage_config

STAGES_DIR = Path(__file__).resolve().parents[2] / "workflow" / "stages"

CANONICAL_STAGES = [
    "literature_review",
    "proposal",
    "modeling",
    "computation",
    "analysis_visualization",
    "writing",
]

GUIDANCE_LIST_FIELDS = [
    "acceptable_inputs",
    "evidence_outputs",
    "recommended_skills",
    "suggested_checks",
    "approval_triggers",
    "handoff_notes",
]


def _stage_paths() -> list[Path]:
    return sorted(STAGES_DIR.glob("*.json"))


def _load_stage(name: str) -> dict:
    return json.loads((STAGES_DIR / f"{name}.json").read_text())


def test_all_canonical_stages_exist():
    for name in CANONICAL_STAGES:
        path = STAGES_DIR / f"{name}.json"
        assert path.exists(), f"Missing canonical stage: {name}"


def test_legacy_alias_stages_are_rejected():
    for name in ["literature", "review", "input_generation", "compute", "analysis", "visualization"]:
        assert not (STAGES_DIR / f"{name}.json").exists()
        try:
            load_stage_config(name)
        except FileNotFoundError:
            continue
        raise AssertionError(f"legacy stage alias should not load: {name}")


def test_runtime_rejects_legacy_stage_alias_without_alias_file(tmp_path):
    workflow_dir = tmp_path / "workflow"
    stages_dir = workflow_dir / "stages"
    stages_dir.mkdir(parents=True)
    (stages_dir / "computation.json").write_text((STAGES_DIR / "computation.json").read_text(encoding="utf-8"), encoding="utf-8")

    try:
        load_stage_config("compute", workflow_dir=str(workflow_dir))
    except FileNotFoundError:
        return
    raise AssertionError("legacy compute stage alias should not load")


def test_all_stage_json_valid():
    paths = _stage_paths()
    assert paths, "No stage files found"
    for path in paths:
        data = json.loads(path.read_text())
        assert isinstance(data, dict), f"Stage {path.name} is not a dict"


def test_stage_name_matches_filename():
    for path in _stage_paths():
        data = json.loads(path.read_text())
        assert data["name"] == path.stem, f"Stage {path.name} name mismatch: {data.get('name')}"


def test_stage_has_open_guidance_contract():
    for path in _stage_paths():
        data = json.loads(path.read_text())
        assert data.get("intent"), f"Stage {path.name} missing intent"
        for field in GUIDANCE_LIST_FIELDS:
            assert field in data, f"Stage {path.name} missing {field}"
            assert isinstance(data[field], list), f"Stage {path.name} {field} is not a list"
        assert data["evidence_outputs"], f"Stage {path.name} must define evidence outputs"
        assert data["handoff_notes"], f"Stage {path.name} must define handoff notes"


def test_computation_stages_have_approval_triggers():
    required = {"real_hpc_submit", "remote_execution", "local_job_submit"}
    data = _load_stage("computation")
    triggers = set(data.get("approval_triggers", []))
    assert required.issubset(triggers), "computation missing compute approval triggers"


def test_stage_contracts_do_not_force_fixed_helpers():
    forbidden_keys = {
        "default_parser",
        "fixed_parser",
        "fixed_builder",
        "fixed_report",
        "fixed_report_file",
        "fixed_validators",
    }
    for path in _stage_paths():
        data = json.loads(path.read_text())
        present = forbidden_keys.intersection(data)
        assert not present, f"Stage {path.name} contains hard helper keys: {sorted(present)}"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        print(f"  {t.__name__}...", end=" ")
        t()
        print("OK")
    print(f"\n  All {len(tests)} tests passed!")
