"""Workflow and recipe loading helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WORKFLOW_DIR = ROOT / "workflow"

CANONICAL_STAGES = {
    "literature_review",
    "proposal",
    "modeling",
    "computation",
    "analysis_visualization",
    "writing",
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
    """Return a canonical stage name or raise for non-canonical input."""
    if stage not in CANONICAL_STAGES:
        raise ValueError(f"Unknown canonical stage: {stage}")
    return stage


def canonical_stage_sequence(stages: list[str | dict[str, Any]]) -> list[str]:
    """Validate canonical stages and remove duplicates while preserving order."""
    sequence: list[str] = []
    seen: set[str] = set()
    for stage in stages:
        canonical = canonical_stage_name(_stage_name(stage))
        if canonical in seen:
            continue
        sequence.append(canonical)
        seen.add(canonical)
    return sequence


def load_recipe(
    name: str,
    *,
    workflow_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Load a JSON recipe by canonical recipe name."""
    base = _workflow_dir(workflow_dir)
    recipe_path = base / "recipes" / f"{name}.json"
    if recipe_path.is_file():
        return _read_json(recipe_path)

    raise FileNotFoundError(f"Recipe not found: {name}")


def list_recipes(
    *,
    workflow_dir: str | Path | None = None,
) -> list[str]:
    """List available canonical JSON recipes."""
    base = _workflow_dir(workflow_dir)
    return sorted(path.stem for path in (base / "recipes").glob("*.json"))
