import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_claude_source_manifests_are_separate_from_codex():
    plugin = read_json(ROOT / ".claude-plugin" / "plugin.json")
    marketplace = read_json(ROOT / ".claude-plugin" / "marketplace.json")
    codex_plugin = read_json(ROOT / ".codex-plugin" / "plugin.json")
    codex_marketplace = read_json(ROOT / ".agents" / "plugins" / "marketplace.json")

    assert plugin["name"] == "simflow"
    assert plugin["mcpServers"] == "./.claude.mcp.json"
    assert "interface" not in plugin
    assert "hooks" not in plugin

    simflow_entry = next(entry for entry in marketplace["plugins"] if entry["name"] == "simflow")
    assert simflow_entry["source"] == "./"
    assert "version" not in simflow_entry
    assert "mcpServers" not in simflow_entry

    assert codex_plugin["mcpServers"] == "./.mcp.json"
    assert codex_marketplace["name"] == "simflow-source"


def test_claude_mcp_config_uses_plugin_root_substitution():
    mcp = read_json(ROOT / ".claude.mcp.json")
    servers = mcp["mcpServers"]

    assert set(servers) == {
        "simflow_state",
        "artifact_store",
        "checkpoint_store",
        "literature",
        "structure",
        "hpc",
        "parsers",
    }
    for name, server in servers.items():
        assert server["command"] == "python3"
        assert server["args"] == [
            "${CLAUDE_PLUGIN_ROOT}/scripts/start_mcp_server.py",
            name,
        ]
        assert server["cwd"] == "${CLAUDE_PLUGIN_ROOT}"


def test_claude_marketplace_wrapper_builds_expected_shape(tmp_path):
    wrapper = tmp_path / "claude-marketplace"
    subprocess.run(
        [
            "node",
            str(ROOT / "scripts" / "build_claude_marketplace_wrapper.js"),
            str(wrapper),
            "--marketplace-name=test-simflow-claude",
        ],
        cwd=ROOT,
        check=True,
    )

    marketplace = read_json(wrapper / ".claude-plugin" / "marketplace.json")
    entry = marketplace["plugins"][0]
    plugin_root = wrapper / "plugins" / "simflow"

    assert marketplace["name"] == "test-simflow-claude"
    assert entry["name"] == "simflow"
    assert entry["source"] == "./plugins/simflow"
    assert "version" not in entry
    assert (plugin_root / ".claude-plugin" / "plugin.json").is_file()
    assert (plugin_root / ".claude.mcp.json").is_file()
    assert (plugin_root / "scripts" / "start_mcp_server.py").is_file()
    assert (plugin_root / "skills" / "simflow" / "SKILL.md").is_file()
    assert (plugin_root / "mcp").is_dir()
    assert (plugin_root / "runtime").is_dir()
    assert not (plugin_root / "tests").exists()
    assert not (plugin_root / ".simflow").exists()
    assert not (plugin_root / ".omx").exists()


def test_claude_validator_accepts_built_wrapper(tmp_path):
    wrapper = tmp_path / "claude-marketplace"
    subprocess.run(
        [
            "node",
            str(ROOT / "scripts" / "build_claude_marketplace_wrapper.js"),
            str(wrapper),
        ],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        ["node", str(ROOT / "scripts" / "validate_claude_plugin.js")],
        cwd=ROOT,
        env={**os.environ, "SIMFLOW_CLAUDE_MARKETPLACE_ROOT": str(wrapper)},
        check=True,
    )
