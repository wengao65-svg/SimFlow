import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKAGED_SKILLS = {
    "simflow",
    "simflow-literature-review",
    "simflow-proposal",
    "simflow-modeling",
    "simflow-computation",
    "simflow-analysis-visualization",
    "simflow-writing",
    "simflow-safety-gates",
    "simflow-vasp",
    "simflow-qe",
    "simflow-cp2k",
    "simflow-lammps",
    "simflow-gaussian",
    "simflow-checkpoint",
    "simflow-handoff",
    "simflow-verify",
}
FORBIDDEN_SOURCE_PATHS = [
    "agents",
    "workflow/workflows",
    "workflow/stages/literature.json",
    "workflow/stages/review.json",
    "workflow/stages/input_generation.json",
    "workflow/stages/compute.json",
    "workflow/stages/analysis.json",
    "workflow/stages/visualization.json",
    "runtime/scripts",
    "skills/simflow-pipeline",
    "skills/simflow-stage",
    "skills/simflow-compute",
    "skills/simflow-input-generation",
    "skills/simflow-literature",
    "skills/simflow-analysis",
    "skills/simflow-visualization",
    "skills/simflow-review",
    "skills/simflow-plan",
    "skills/simflow-intake",
    "skills/simflow-ralph",
    "skills/simflow-team",
]
RESTRICTED_VASP_NAMES = {"POTCAR", "WAVECAR", "CHGCAR", "OUTCAR", "vasprun.xml"}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def assert_canonical_package_surface(plugin_root: Path) -> None:
    packaged = {path.parent.name for path in (plugin_root / "skills").glob("*/SKILL.md")}
    assert PACKAGED_SKILLS.issubset(packaged)
    assert packaged.issubset(PACKAGED_SKILLS)
    assert (plugin_root / "runtime" / "simflow_core").is_dir()
    assert (plugin_root / "runtime" / "simflow_helpers").is_dir()
    for relative_path in FORBIDDEN_SOURCE_PATHS:
        assert not (plugin_root / relative_path).exists(), relative_path
    for name in [
        "literature_review",
        "proposal",
        "modeling",
        "computation",
        "analysis_visualization",
        "writing",
    ]:
        assert (plugin_root / "workflow" / "stages" / f"{name}.json").is_file()
    for name in ["dft", "aimd", "classical_md", "phonon", "neb", "custom"]:
        assert (plugin_root / "workflow" / "recipes" / f"{name}.json").is_file()
    restricted = [path for path in plugin_root.rglob("*") if path.name in RESTRICTED_VASP_NAMES]
    assert restricted == []


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
    assert_canonical_package_surface(plugin_root)


def test_codex_marketplace_wrapper_builds_canonical_surface(tmp_path):
    wrapper = tmp_path / "codex-marketplace"
    subprocess.run(
        [
            "node",
            str(ROOT / "scripts" / "build_marketplace_wrapper.js"),
            str(wrapper),
            "--marketplace-name=test-simflow-codex",
        ],
        cwd=ROOT,
        check=True,
    )

    marketplace = read_json(wrapper / ".agents" / "plugins" / "marketplace.json")
    entry = marketplace["plugins"][0]
    plugin_root = wrapper / "plugins" / "simflow"

    assert marketplace["name"] == "test-simflow-codex"
    assert entry["name"] == "simflow"
    assert entry["source"]["path"] == "./plugins/simflow"
    assert (plugin_root / ".codex-plugin" / "plugin.json").is_file()
    assert (plugin_root / ".mcp.json").is_file()
    assert (plugin_root / "scripts" / "start_mcp_server.py").is_file()
    assert_canonical_package_surface(plugin_root)


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
