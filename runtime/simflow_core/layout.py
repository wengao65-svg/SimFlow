"""Advisory project-layout and analysis-placement helpers.

Layout guidance is deliberately read-only. These helpers never create, move,
rename, or reject user directories.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Iterable

from .state import resolve_project_path, resolve_project_root


RECOMMENDED_PHASES = (
    "phase1_literature_review",
    "phase2_proposal",
    "phase3_modeling",
    "phase4_computation",
    "phase5_analysis_visualization",
    "phase6_writing",
)

TECHNICAL_CONTAINERS = {
    "run",
    "runs",
    "case",
    "cases",
    "output",
    "outputs",
    "raw",
    "data",
    "cache",
    "work",
    "tmp",
    "temporary",
}

ANALYSIS_NAMES = ("analysis", "results")
_PHASE_PATTERN = re.compile(r"^phase\d+_")
_STAGE_PATTERN = re.compile(r"^stage\d+_")
_VARIANT_PATTERN = re.compile(r"^(run|case|replica|seed|temperature|temp)[_-]?\w*$", re.IGNORECASE)


def _relative(path: Path, root: Path) -> str:
    return "." if path == root else str(path.relative_to(root))


def _ancestors_inside(path: Path, root: Path) -> list[Path]:
    result = []
    current = path
    while True:
        result.append(current)
        if current == root:
            break
        current = current.parent
    return result


def _named_ancestor(path: Path, root: Path, pattern: re.Pattern[str]) -> Path | None:
    for candidate in _ancestors_inside(path, root):
        if pattern.match(candidate.name):
            return candidate
    return None


def _semantic_unit(path: Path, root: Path) -> Path:
    current = path.parent if path.suffix or path.is_file() else path
    while current != root and (
        current.name.lower() in TECHNICAL_CONTAINERS
        or _VARIANT_PATTERN.match(current.name)
    ):
        current = current.parent
    return current


def _semantic_common_parent(paths: Iterable[Path], root: Path) -> Path:
    units = [_semantic_unit(path, root) for path in paths]
    common = Path(os.path.commonpath([str(path) for path in units]))
    while common != root and common.name.lower() in TECHNICAL_CONTAINERS:
        common = common.parent
    return common


def _analysis_root(scope: Path) -> Path:
    if scope.name.lower() in ANALYSIS_NAMES:
        return scope
    for name in ANALYSIS_NAMES:
        candidate = scope / name
        if candidate.is_dir():
            return candidate
    return scope / "analysis"


def _topic_name(topic: str | None) -> str | None:
    if not topic:
        return None
    normalized = re.sub(r"[^a-z0-9]+", "_", topic.strip().lower()).strip("_")
    return normalized or None


def inspect_layout(project_root: str) -> dict[str, Any]:
    """Describe the existing layout and non-blocking organization signals."""
    root = resolve_project_root(project_root=project_root)
    top_level = sorted(path.name for path in root.iterdir()) if root.is_dir() else []
    phases = [name for name in top_level if _PHASE_PATTERN.match(name)]
    bare_stages = [name for name in top_level if _STAGE_PATTERN.match(name)]
    nested_state = sorted(
        str(path.relative_to(root))
        for path in root.rglob(".simflow")
        if path != root / ".simflow" and path.is_dir()
    )
    navigation = [
        name for name in ("README.md", "workflow.md")
        if (root / name).is_file()
    ]
    return {
        "project_root": str(root),
        "existing_top_level": top_level,
        "existing_phases": phases,
        "bare_stage_directories": bare_stages,
        "nested_simflow_directories": nested_state,
        "navigation_files": navigation,
        "recommended_template": list(RECOMMENDED_PHASES),
        "enforcement": "advisory",
        "requires_migration": False,
    }


def recommend_analysis_location(
    project_root: str,
    input_paths: list[str],
    *,
    topic: str | None = None,
    project_level: bool = False,
) -> dict[str, Any]:
    """Recommend one authoritative analysis location from consumed inputs.

    The recommendation follows semantic scope rather than the literal deepest
    common path. Pure containers such as ``runs/`` and ``outputs/`` are not
    promoted into user-facing analysis roots.
    """
    if not input_paths:
        raise ValueError("input_paths is required")
    root = resolve_project_root(project_root=project_root)
    resolved = [resolve_project_path(path, project_root=str(root)) for path in input_paths]
    units = [_semantic_unit(path, root) for path in resolved]
    phases = {_named_ancestor(path, root, _PHASE_PATTERN) for path in units}
    stages = {_named_ancestor(path, root, _STAGE_PATTERN) for path in units}
    phases.discard(None)
    stages.discard(None)

    scope_kind: str
    if project_level:
        phase5 = next(
            (
                root / name
                for name in ("phase5_analysis_visualization", "phase5_analysis")
                if (root / name).is_dir()
            ),
            root / "phase5_analysis_visualization",
        )
        scope = phase5
        analysis_root = phase5
        scope_kind = "project"
    elif len(stages) == 1:
        scope = next(iter(stages))
        analysis_root = _analysis_root(scope)
        scope_kind = "stage"
    elif len(phases) == 1:
        scope = next(iter(phases))
        analysis_root = _analysis_root(scope)
        scope_kind = "phase"
    else:
        scope = _semantic_common_parent(resolved, root)
        analysis_root = _analysis_root(scope)
        scope_kind = "calculation_unit" if len(units) == 1 else "common_parent"

    normalized_topic = _topic_name(topic)
    authoritative = analysis_root / normalized_topic if normalized_topic else analysis_root
    navigation_root = analysis_root
    project_index = None
    if project_level:
        project_index = analysis_root / "README.md"
    elif (root / "phase5_analysis_visualization").is_dir():
        project_index = root / "phase5_analysis_visualization" / "README.md"
    elif (root / "phase5_analysis").is_dir():
        project_index = root / "phase5_analysis" / "README.md"
    elif (root / "README.md").is_file():
        project_index = root / "README.md"
    else:
        project_index = root / ".simflow" / "reports" / "analysis_index.md"

    return {
        "scope": scope_kind,
        "scope_root": _relative(scope, root),
        "authoritative_location": _relative(authoritative, root),
        "analysis_entry": _relative(navigation_root / "README.md", root),
        "project_index": _relative(project_index, root),
        "input_units": [_relative(path, root) for path in units],
        "project_level": project_level,
        "actions": {
            "create_or_update_entry": True,
            "copy_results": False,
            "create_symlink": False,
            "move_existing_outputs": False,
        },
        "note": "Recommendation only; preserve existing names and relative paths unless the user approves a migration.",
    }

