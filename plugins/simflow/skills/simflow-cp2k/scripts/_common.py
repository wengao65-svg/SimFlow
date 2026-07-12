"""Shared I/O helpers for the simflow-cp2k skill wrappers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SIMFLOW_ROOT = Path(__file__).resolve().parents[3]
import sys

if str(SIMFLOW_ROOT) not in sys.path:
    sys.path.insert(0, str(SIMFLOW_ROOT))

from runtime.simflow_core.state import resolve_project_path, resolve_project_root


def resolve_cp2k_paths(project_root: str, calc_dir: str = ".") -> tuple[Path, Path]:
    """Resolve project_root and calc_dir without writing workflow state."""
    root = resolve_project_root(project_root=project_root)
    work_dir = resolve_project_path(calc_dir, project_root=str(root))
    return root, work_dir


def write_json_verified(root: Path, relative_path: str, data: dict[str, Any]) -> str:
    """Write JSON under project_root and re-read it for verification."""
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    json.loads(path.read_text(encoding="utf-8"))
    return relative_path
