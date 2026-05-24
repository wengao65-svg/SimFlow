#!/usr/bin/env python3
"""Tests for JSON recipe definitions."""

import json
from pathlib import Path

from runtime.simflow_core.workflow import (
    canonical_stage_sequence,
    list_recipes,
    load_recipe,
)

ROOT = Path(__file__).resolve().parents[2]
RECIPES_DIR = ROOT / "workflow" / "recipes"

EXPECTED_RECIPES = ["dft", "aimd", "classical_md", "phonon", "neb", "custom"]
CANONICAL_STAGES = {"literature_review", "proposal", "modeling", "computation", "analysis_visualization", "writing"}
REQUIRED_RECIPE_FIELDS = ["name", "recipe_type", "intent", "stages", "evidence_outputs", "recommended_checks", "approval_triggers"]


def _load_recipe(name: str) -> dict:
    return json.loads((RECIPES_DIR / f"{name}.json").read_text())


def test_recipe_directory_uses_json_only():
    assert RECIPES_DIR.is_dir(), "workflow/recipes directory is missing"
    non_json = [path.name for path in RECIPES_DIR.iterdir() if path.is_file() and path.suffix != ".json"]
    assert not non_json, f"Recipes must be JSON-only in this refactor: {non_json}"


def test_expected_recipe_files_exist():
    for name in EXPECTED_RECIPES:
        assert (RECIPES_DIR / f"{name}.json").is_file(), f"Missing recipe: {name}"


def test_recipe_json_valid():
    for path in sorted(RECIPES_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        assert isinstance(data, dict), f"Recipe {path.name} is not a dict"


def test_recipe_has_open_contract_fields():
    for path in sorted(RECIPES_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        for field in REQUIRED_RECIPE_FIELDS:
            assert field in data, f"Recipe {path.name} missing {field}"
        assert data["name"] == path.stem
        assert isinstance(data["stages"], list) and data["stages"]


def test_recipe_stages_use_canonical_stage_names():
    for path in sorted(RECIPES_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        unknown = [stage for stage in data["stages"] if stage not in CANONICAL_STAGES]
        assert not unknown, f"Recipe {path.name} uses non-canonical stages: {unknown}"


def test_computation_recipes_include_submit_approval_triggers():
    required = {"real_hpc_submit", "remote_execution", "local_job_submit"}
    for path in sorted(RECIPES_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        if "computation" not in data["stages"]:
            continue
        triggers = set(data.get("approval_triggers", []))
        assert required.issubset(triggers), f"Recipe {path.name} missing compute approval triggers"


def test_runtime_lists_json_recipes_only():
    names = set(list_recipes())
    assert names == set(EXPECTED_RECIPES)


def test_runtime_loads_json_recipe():
    recipe = load_recipe("dft")
    assert recipe["name"] == "dft"
    assert recipe["recipe_type"] == "dft"
    assert recipe["stages"] == ["literature_review", "proposal", "modeling", "computation", "analysis_visualization", "writing"]


def test_md_alias_is_not_supported():
    try:
        load_recipe("md")
    except FileNotFoundError:
        return
    raise AssertionError("md alias should not load; use classical_md")


def test_canonical_stage_sequence_rejects_legacy_subactivities():
    try:
        canonical_stage_sequence(["proposal", "input_generation", "compute"])
    except ValueError as exc:
        assert "input_generation" in str(exc)
        return
    raise AssertionError("legacy subactivities should not be accepted as stages")
