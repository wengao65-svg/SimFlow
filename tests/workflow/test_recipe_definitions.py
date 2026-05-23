#!/usr/bin/env python3
"""Tests for JSON recipe definitions."""

import json
from pathlib import Path

from runtime.lib.workflow import (
    canonical_stage_sequence,
    convert_legacy_workflow_to_recipe,
    list_recipes,
    load_recipe,
)

ROOT = Path(__file__).resolve().parents[2]
RECIPES_DIR = ROOT / "workflow" / "recipes"
LEGACY_WORKFLOWS_DIR = ROOT / "workflow" / "workflows"

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


def test_runtime_lists_json_and_legacy_recipes():
    names = set(list_recipes())
    assert set(EXPECTED_RECIPES).issubset(names)
    assert "md" in names


def test_runtime_loads_json_recipe_before_legacy_workflow():
    recipe = load_recipe("dft")
    assert recipe["name"] == "dft"
    assert recipe["recipe_type"] == "dft"
    assert recipe["legacy_source"]["type"] == "recipe"
    assert recipe["stages"] == ["literature_review", "proposal", "modeling", "computation", "analysis_visualization", "writing"]


def test_runtime_loads_md_alias_as_classical_md_recipe():
    recipe = load_recipe("md")
    assert recipe["name"] == "classical_md"
    assert recipe["recipe_type"] == "classical_md"
    assert recipe["legacy_source"]["type"] == "recipe"
    assert recipe["legacy_requested_name"] == "md"
    assert recipe["stages"] == ["proposal", "modeling", "computation", "analysis_visualization", "writing"]


def test_runtime_loads_md_alias_without_legacy_workflow_files(tmp_path):
    workflow_dir = tmp_path / "workflow"
    recipes_dir = workflow_dir / "recipes"
    recipes_dir.mkdir(parents=True)
    (recipes_dir / "classical_md.json").write_text((RECIPES_DIR / "classical_md.json").read_text(encoding="utf-8"), encoding="utf-8")

    recipe = load_recipe("md", workflow_dir=workflow_dir)

    assert recipe["name"] == "classical_md"
    assert recipe["legacy_requested_name"] == "md"


def test_legacy_workflow_conversion_preserves_lineage_context():
    legacy = json.loads((LEGACY_WORKFLOWS_DIR / "dft.json").read_text())
    recipe = convert_legacy_workflow_to_recipe(legacy, source_path=LEGACY_WORKFLOWS_DIR / "dft.json")
    assert recipe["recipe_type"] == "dft"
    assert recipe["legacy_stage_dependencies"] == legacy["stage_dependencies"]
    assert recipe["default_entry"] == "literature_review"
    assert recipe["stages"] == ["literature_review", "proposal", "modeling", "computation", "analysis_visualization", "writing"]


def test_canonical_stage_sequence_deduplicates_legacy_subactivities():
    stages = ["literature", "review", "proposal", "input_generation", "compute", "analysis", "visualization", "writing"]
    assert canonical_stage_sequence(stages) == [
        "literature_review",
        "proposal",
        "computation",
        "analysis_visualization",
        "writing",
    ]
