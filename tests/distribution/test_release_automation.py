"""Release automation smoke tests."""

from __future__ import annotations

import json
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
    assert "OpenCode source adapter exists" in result.stdout
    assert "OpenCode canonical plugin module exists" in result.stdout
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


def test_distribution_publish_workflows_cover_supported_hosts():
    codex = ROOT / ".github" / "workflows" / "publish-codex-marketplace.yml"
    claude = ROOT / ".github" / "workflows" / "publish-claude-marketplace.yml"
    opencode = ROOT / ".github" / "workflows" / "publish-opencode-plugin.yml"

    assert codex.exists()
    assert claude.exists()
    assert opencode.exists()

    codex_text = codex.read_text()
    claude_text = claude.read_text()
    opencode_text = opencode.read_text()

    assert "npm run build:codex-marketplace" in codex_text
    assert "npm run publish:codex-marketplace -- --no-build" in codex_text
    assert "npm run build:claude-marketplace" in claude_text
    assert "SIMFLOW_CLAUDE_MARKETPLACE_ROOT=dist/claude-marketplace npm run validate:claude-plugin" in claude_text
    assert "npm run publish:claude-marketplace -- --no-build" in claude_text
    assert "npm run build:opencode-plugin" in opencode_text
    assert "SIMFLOW_OPENCODE_PLUGIN_ROOT=dist/opencode-plugin npm run validate:opencode-plugin" in opencode_text
    assert "npm run publish:opencode-plugin -- --no-build" in opencode_text
    assert "NODE_AUTH_TOKEN: ${{ secrets.SIMFLOW }}" in opencode_text
    assert "secrets.NPM_TOKEN" not in opencode_text


def test_main_ci_runs_isolated_opencode_smoke():
    workflow = (ROOT / ".github" / "workflows" / "test.yml").read_text()

    assert workflow.count("fetch-depth: 0") == 2
    assert "opencode-ai@1.18.9" in workflow
    assert "npm run build:opencode-plugin" in workflow
    assert "node scripts/smoke_opencode_plugin.js dist/opencode-plugin" in workflow


def test_opencode_smoke_accepts_supported_stable_1x_versions():
    versions = [
        "1.18.8",
        "1.18.9",
        "1.18.10",
        "1.19.0",
        "1.99.0+build.1",
        "2.0.0",
        "1.19.0-beta.1",
        "not-a-version",
    ]
    script = """
const { isSupportedOpenCodeVersion } = require('./scripts/smoke_opencode_plugin.js');
const versions = JSON.parse(process.argv[1]);
process.stdout.write(JSON.stringify(versions.map(isSupportedOpenCodeVersion)));
"""

    result = subprocess.run(
        ["node", "-e", script, json.dumps(versions)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == [False, True, True, True, True, False, False, False]


def test_marketplace_ref_resolution_falls_back_to_origin(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "SimFlow Test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@simflow.local"], cwd=repo, check=True)
    (repo / "README.md").write_text("fixture\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "fixture"], cwd=repo, check=True)
    subprocess.run(
        ["git", "update-ref", "refs/remotes/origin/codex-marketplace", "HEAD"],
        cwd=repo,
        check=True,
    )

    script = """
const { resolveGitBranchRef } = require(process.argv[1]);
process.stdout.write(resolveGitBranchRef('codex-marketplace', process.argv[2]));
"""
    result = subprocess.run(
        [
            "node",
            "-e",
            script,
            str(ROOT / "scripts" / "marketplace_version_guard.js"),
            str(repo),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == "refs/remotes/origin/codex-marketplace"


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
