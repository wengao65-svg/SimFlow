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
