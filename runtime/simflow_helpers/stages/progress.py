"""Helpers for compatibility stage progress.

These helpers keep the legacy stage-runner skills thin while the runtime
migrates toward canonical workflow-layer packages.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from runtime.simflow_core.workflow import compatibility_activity_sequence, load_recipe


def resolve_project_root_from_workflow_dir(workflow_dir: str) -> Path:
    """Resolve the project root from either a project root or .simflow path."""
    path = Path(workflow_dir).expanduser().resolve()
    return path.parent if path.name == ".simflow" else path


def load_workflow_activities(workflow_type: str, metadata: dict[str, Any] | None = None) -> list[str]:
    """Load executable activities from metadata or canonical recipes."""
    metadata = metadata or {}
    stages = metadata.get("stages", [])
    if isinstance(stages, list) and stages:
        return stages

    normalized = (workflow_type or "dft").lower()
    recipe = load_recipe(normalized)
    return compatibility_activity_sequence(recipe.get("stages", []))


def get_activities_to_run(
    activities: list[str],
    current_activity: str,
    stage_registry: dict[str, Any],
    target_activity: str | None,
) -> list[str]:
    """Determine which compatibility activities the pipeline should traverse."""
    if not activities:
        return []

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

