"""Workflow and recipe loading helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WORKFLOW_DIR = ROOT / "workflow"

LEGACY_STAGE_MAP = {
    "literature": "literature_review",
    "review": "literature_review",
    "proposal": "proposal",
    "modeling": "modeling",
    "input_generation": "computation",
    "compute": "computation",
    "analysis": "analysis_visualization",
    "visualization": "analysis_visualization",
    "writing": "writing",
}

LEGACY_RECIPE_TYPE_MAP = {
    "md": "classical_md",
}


def _workflow_dir(workflow_dir: str | Path | None = None) -> Path:
    return Path(workflow_dir).resolve() if workflow_dir is not None else DEFAULT_WORKFLOW_DIR


def _read_json(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _stage_name(stage: str | dict[str, Any]) -> str:
    if isinstance(stage, str):
        return stage
    if isinstance(stage, dict) and isinstance(stage.get("name"), str):
        return stage["name"]
    raise ValueError(f"Invalid stage entry: {stage!r}")


def canonical_stage_name(stage: str) -> str:
    """Map a legacy or canonical stage name to the canonical open stage name."""
    return LEGACY_STAGE_MAP.get(stage, stage)


def canonical_stage_sequence(stages: list[str | dict[str, Any]]) -> list[str]:
    """Map stages to canonical names and remove duplicates while preserving order."""
    sequence: list[str] = []
    seen: set[str] = set()
    for stage in stages:
        canonical = canonical_stage_name(_stage_name(stage))
        if canonical in seen:
            continue
        sequence.append(canonical)
        seen.add(canonical)
    return sequence


def convert_legacy_workflow_to_recipe(
    workflow: dict[str, Any],
    *,
    source_path: str | Path | None = None,
) -> dict[str, Any]:
    """Convert a legacy workflow definition into an open recipe record."""
    name = workflow.get("workflow_name") or workflow.get("name")
    if not isinstance(name, str) or not name:
        raise ValueError("Legacy workflow is missing name/workflow_name")

    legacy_stages = workflow.get("stages", [])
    if not isinstance(legacy_stages, list) or not legacy_stages:
        raise ValueError(f"Legacy workflow {name} has no stages")

    recipe_type = LEGACY_RECIPE_TYPE_MAP.get(name, workflow.get("workflow_type") or name)
    canonical_stages = canonical_stage_sequence(legacy_stages)
    entry_points = [
        canonical_stage_name(entry)
        for entry in workflow.get("entry_points", [])
        if isinstance(entry, str)
    ]
    default_entry = workflow.get("default_entry") or workflow.get("entry_point")
    if isinstance(default_entry, str):
        default_entry = canonical_stage_name(default_entry)

    recipe = {
        "name": name,
        "recipe_type": recipe_type,
        "intent": workflow.get("description") or f"Legacy {name} workflow converted to an open recipe.",
        "description": workflow.get("description", ""),
        "tags": [name, recipe_type, "legacy_workflow"],
        "stages": canonical_stages,
        "legacy_stages": [_stage_name(stage) for stage in legacy_stages],
        "legacy_stage_dependencies": workflow.get("stage_dependencies", {}),
        "entry_points": sorted(set(entry_points), key=entry_points.index) if entry_points else canonical_stages,
        "default_entry": default_entry or (canonical_stages[0] if canonical_stages else None),
        "evidence_outputs": ["artifact_registry", "checkpoint_records", "handoff_summary"],
        "recommended_checks": ["legacy stage mapping reviewed", "artifact lineage preserved", "approval triggers reviewed"],
        "approval_triggers": ["real_hpc_submit", "remote_execution", "local_job_submit"],
        "handoff_notes": ["This recipe was converted from a legacy workflow definition; preserve legacy artifacts and checkpoints during migration."],
        "legacy_source": {
            "type": "workflow",
            "path": str(source_path) if source_path is not None else None,
        },
    }
    return recipe


def load_recipe(
    name: str,
    *,
    workflow_dir: str | Path | None = None,
    include_legacy: bool = True,
) -> dict[str, Any]:
    """Load a JSON recipe, optionally falling back to a legacy workflow."""
    base = _workflow_dir(workflow_dir)
    recipe_path = base / "recipes" / f"{name}.json"
    if recipe_path.is_file():
        recipe = _read_json(recipe_path)
        recipe.setdefault("legacy_source", {"type": "recipe", "path": str(recipe_path)})
        return recipe

    legacy_path = base / "workflows" / f"{name}.json"
    if include_legacy and legacy_path.is_file():
        return convert_legacy_workflow_to_recipe(_read_json(legacy_path), source_path=legacy_path)

    raise FileNotFoundError(f"Recipe not found: {name}")


def list_recipes(
    *,
    workflow_dir: str | Path | None = None,
    include_legacy: bool = True,
) -> list[str]:
    """List available JSON recipes and, optionally, legacy workflow fallbacks."""
    base = _workflow_dir(workflow_dir)
    names = {path.stem for path in (base / "recipes").glob("*.json")}
    if include_legacy:
        names.update(path.stem for path in (base / "workflows").glob("*.json"))
    return sorted(names)
