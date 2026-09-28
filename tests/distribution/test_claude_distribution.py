import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKAGED_SKILLS = {
    "simflow-literature-review",
    "simflow-reference-extraction",
    "simflow-proposal",
    "simflow-modeling",
    "simflow-computation",
    "simflow-analysis-visualization",
    "simflow-writing",
    "simflow-vasp",
    "simflow-cp2k",
    "simflow-lammps",
    "simflow-gpumd",
    "simflow-mlp",
}
FORBIDDEN_SOURCE_PATHS = [
    "agents",
    "notifications",
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
    assert packaged == PACKAGED_SKILLS
    for retired in ["runtime", "mcp", "workflow", "schemas", ".mcp.json", ".claude.mcp.json"]:
        assert not (plugin_root / retired).exists(), retired
    restricted = [path for path in plugin_root.rglob("*") if path.name in RESTRICTED_VASP_NAMES]
    assert restricted == []


def test_claude_source_manifests_are_separate_from_codex():
    plugin = read_json(ROOT / ".claude-plugin" / "plugin.json")
    marketplace = read_json(ROOT / ".claude-plugin" / "marketplace.json")
    codex_plugin = read_json(ROOT / ".codex-plugin" / "plugin.json")
    codex_marketplace = read_json(ROOT / ".agents" / "plugins" / "marketplace.json")

    assert plugin["name"] == "simflow"
    assert "mcpServers" not in plugin
    assert "interface" not in plugin
    assert "hooks" not in plugin

    simflow_entry = next(entry for entry in marketplace["plugins"] if entry["name"] == "simflow")
    assert simflow_entry["source"] == "./"
    assert "version" not in simflow_entry
    assert "mcpServers" not in simflow_entry

    assert "mcpServers" not in codex_plugin
    assert codex_marketplace["name"] == "simflow-source"


def test_claude_does_not_register_mcp():
    assert not (ROOT / ".claude.mcp.json").exists()
    assert not (ROOT / ".mcp.json").exists()


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
