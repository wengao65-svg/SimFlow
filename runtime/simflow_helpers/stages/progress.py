"""Helpers for compatibility stage progress.

These helpers keep the legacy stage-runner skills thin while the runtime
migrates toward canonical workflow-layer packages.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from runtime.simflow_core.workflow import canonical_stage_name, load_recipe


def resolve_project_root_from_workflow_dir(workflow_dir: str) -> Path:
    """Resolve the project root from either a project root or .simflow path."""
    path = Path(workflow_dir).expanduser().resolve()
    return path.parent if path.name == ".simflow" else path


def load_workflow_activities(workflow_type: str, metadata: dict[str, Any] | None = None) -> list[str]:
    """Load canonical workflow stages from metadata or canonical recipes."""
    metadata = metadata or {}
    stages = metadata.get("canonical_stages") or metadata.get("stages", [])
    if isinstance(stages, list) and stages:
        sequence: list[str] = []
        seen: set[str] = set()
        for stage in stages:
            if not isinstance(stage, str):
                continue
            canonical = canonical_stage_name(stage)
            if canonical in seen:
                continue
            sequence.append(canonical)
            seen.add(canonical)
        if sequence:
            return sequence

    normalized = (workflow_type or "dft").lower()
    recipe = load_recipe(normalized)
    return [canonical_stage_name(stage) for stage in recipe.get("stages", []) if isinstance(stage, str)]


def get_activities_to_run(
    activities: list[str],
    current_activity: str,
    stage_registry: dict[str, Any],
    target_activity: str | None,
) -> list[str]:
    """Determine which canonical stages the pipeline should traverse."""
    if not activities:
        return []

    current_activity = canonical_stage_name(current_activity)
    target_activity = canonical_stage_name(target_activity) if target_activity else None
    if current_activity not in activities:
        current_activity = activities[0]

    start_idx = activities.index(current_activity)
    if stage_registry.get(current_activity, {}).get("status") == "completed" and start_idx < len(activities) - 1:
        start_idx += 1

    if target_activity:
        if target_activity not in activities:
            return []
        end_idx = activities.index(target_activity) + 1
        if end_idx < start_idx:
            return []
        return activities[start_idx:end_idx]

    return activities[start_idx:]
