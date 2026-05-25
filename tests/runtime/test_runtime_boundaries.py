import subprocess
import tempfile
import tomllib
from pathlib import Path

import pytest

from runtime.simflow_core.state import init_workflow
from runtime.simflow_core.validation import load_stage_config
from runtime.simflow_core.workflow import load_recipe
from runtime.simflow_helpers.stages.pipeline import run_pipeline


REPO_ROOT = Path(__file__).resolve().parents[2]

CANONICAL_SKILL_DIRS = [
    "skills/simflow-literature-review",
    "skills/simflow-proposal",
    "skills/simflow-modeling",
    "skills/simflow-computation",
    "skills/simflow-analysis-visualization",
    "skills/simflow-writing",
    "skills/simflow-safety-gates",
]

CANONICAL_HELPER_DIRS = [
    "runtime/simflow_helpers/project",
    "runtime/simflow_helpers/stages",
]


def _python_files(relative_dirs: list[str]) -> list[Path]:
    files: list[Path] = []
    for relative_dir in relative_dirs:
        root = REPO_ROOT / relative_dir
        if root.exists():
            files.extend(path for path in root.rglob("*.py") if "__pycache__" not in path.parts)
    return files


def _tracked_files_under(relative_path: str) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", relative_path],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def test_canonical_skill_scripts_use_canonical_runtime_imports():
    offenders = []
    for path in _python_files(CANONICAL_SKILL_DIRS):
        text = path.read_text(encoding="utf-8")
        if "runtime.lib" in text:
            offenders.append(str(path.relative_to(REPO_ROOT)))

    assert offenders == []


def test_canonical_project_and_stage_helpers_use_canonical_runtime_imports():
    offenders = []
    for path in _python_files(CANONICAL_HELPER_DIRS):
        text = path.read_text(encoding="utf-8")
        if "runtime.lib" in text:
            offenders.append(str(path.relative_to(REPO_ROOT)))

    assert offenders == []


def test_removed_source_surfaces_are_not_tracked():
    removed_surfaces = [
        "runtime/lib",
        "runtime/scripts",
        "workflow/workflows",
        "docs/examples",
    ]
    assert {surface: _tracked_files_under(surface) for surface in removed_surfaces} == {
        surface: [] for surface in removed_surfaces
    }


def test_runtime_lib_directory_has_no_python_sources_if_cache_remains():
    runtime_lib = REPO_ROOT / "runtime" / "lib"
    if not runtime_lib.exists():
        return
    assert [path for path in runtime_lib.rglob("*.py") if "__pycache__" not in path.parts] == []


def test_pyproject_does_not_publish_cli_entry_points():
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert "scripts" not in pyproject["project"]


def test_runtime_rejects_removed_recipe_and_stage_aliases():
    with pytest.raises(FileNotFoundError):
        load_recipe("md")
    with pytest.raises(FileNotFoundError):
        load_stage_config("compute")

    with tempfile.TemporaryDirectory() as tmpdir:
        init_workflow("dft", "literature_review", tmpdir)
        result = run_pipeline(str(Path(tmpdir) / ".simflow"), target_stage="compute", dry_run=True)

    assert result["status"] == "error"
    assert result["message"] == "Unknown stage: compute"
