"""Release automation smoke tests."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_release_validation_supports_local_skip_wrapper_mode():
    env = os.environ.copy()
    env["SIMFLOW_RELEASE_ALLOW_DIRTY"] = "1"
    env["SIMFLOW_RELEASE_SKIP_WRAPPERS"] = "1"

    result = subprocess.run(
        ["node", "scripts/validate_release.js"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Version Synchronization" in result.stdout
    assert "Support Matrix" in result.stdout
    assert "Restricted Artifact Scan" in result.stdout
    assert "Workflow Automation" in result.stdout
    assert "Marketplace Version Guard" in result.stdout
    assert "safe dry-run example does not write job records" in result.stdout
    assert "LAMMPS safe dry-run example does not write job records" in result.stdout
    assert "hpc_submit is the only gate allowed to expose submit_job action" in result.stdout
    assert "MLP workflow docs describe readiness as a scientific decision" in result.stdout
    assert "simflow_state tools/list exposes evidence intake tools" in result.stdout
    assert "hpc.submit blocks before execution when workflow state is absent" in result.stdout
    assert "wrapper build validation skipped" in result.stdout
    assert "Errors: 0" in result.stdout


def test_release_notes_command_emits_markdown():
    result = subprocess.run(
        ["node", "scripts/generate_release_notes.js", "--since=HEAD~1"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "# SimFlow Release Notes" in result.stdout
    assert "## Release Gates" in result.stdout
    assert "## Commits" in result.stdout


def test_marketplace_publish_workflows_cover_codex_and_claude():
    codex = ROOT / ".github" / "workflows" / "publish-codex-marketplace.yml"
    claude = ROOT / ".github" / "workflows" / "publish-claude-marketplace.yml"

    assert codex.exists()
    assert claude.exists()

    codex_text = codex.read_text()
    claude_text = claude.read_text()

    assert "npm run build:codex-marketplace" in codex_text
    assert "npm run publish:codex-marketplace -- --no-build" in codex_text
    assert "npm run build:claude-marketplace" in claude_text
    assert "SIMFLOW_CLAUDE_MARKETPLACE_ROOT=dist/claude-marketplace npm run validate:claude-plugin" in claude_text
    assert "npm run publish:claude-marketplace -- --no-build" in claude_text


def _write_minimal_plugin(root: Path, version: str, skills: set[str]) -> None:
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".claude-plugin" / "plugin.json").write_text(
        f'{{"name":"simflow","version":"{version}"}}\n',
        encoding="utf-8",
    )
    for skill in skills:
        skill_dir = root / "skills" / skill
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {skill}\ndescription: test skill\n---\n",
            encoding="utf-8",
        )


def test_marketplace_skill_changes_require_plugin_version_bump(tmp_path):
    previous_skills = {"simflow", "simflow-vasp"}
    current_skills = previous_skills | {"simflow-gpumd", "simflow-mlp"}
    previous = tmp_path / "previous"
    current_same_version = tmp_path / "current-same-version"
    current_new_version = tmp_path / "current-new-version"

    _write_minimal_plugin(previous, "0.8.12", previous_skills)
    _write_minimal_plugin(current_same_version, "0.8.12", current_skills)
    _write_minimal_plugin(current_new_version, "0.8.13", current_skills)

    failed = subprocess.run(
        [
            "node",
            "scripts/check_marketplace_version_guard.js",
            str(current_same_version),
            str(previous),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert failed.returncode == 1
    assert "plugin version must increase when packaged skills change" in failed.stderr
    assert "simflow-gpumd" in failed.stderr
    assert "simflow-mlp" in failed.stderr

    passed = subprocess.run(
        [
            "node",
            "scripts/check_marketplace_version_guard.js",
            str(current_new_version),
            str(previous),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert passed.returncode == 0, passed.stdout + passed.stderr
    assert "marketplace packaged skill/version guard passed" in passed.stdout
