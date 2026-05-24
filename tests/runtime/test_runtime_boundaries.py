from pathlib import Path


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

