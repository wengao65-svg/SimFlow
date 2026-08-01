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
    "simflow-gpumd",
    "simflow-mlp",
    "simflow-gaussian",
    "simflow-checkpoint",
    "simflow-handoff",
    "simflow-verify",
}
RESTRICTED_NAMES = {"POTCAR", "WAVECAR", "CHGCAR", "OUTCAR", "vasprun.xml"}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_opencode_source_adapter_is_dependency_free_and_local():
    loader = ROOT / ".opencode" / "plugins" / "simflow.js"
    module = ROOT / "opencode" / "simflow.mjs"

    assert loader.is_file()
    assert module.is_file()
    assert "../../opencode/simflow.mjs" in loader.read_text(encoding="utf-8")
    text = module.read_text(encoding="utf-8")
    assert 'id: "simflow"' in text
    assert "config.skills.paths" in text
    assert "SIMFLOW_PYTHON" in text
    assert "permission" not in text


def test_opencode_package_builds_canonical_surface(tmp_path):
    output = tmp_path / "opencode-plugin"
    subprocess.run(
        ["node", "scripts/build_opencode_plugin.js", str(output)],
        cwd=ROOT,
        check=True,
    )

    manifest = read_json(output / "package.json")
    assert manifest["name"] == "opencode-simflow"
    assert manifest["version"] == read_json(ROOT / "package.json")["version"]
    assert manifest["exports"]["./server"] == "./index.mjs"
    assert manifest["engines"]["opencode"] == ">=1.18.9 <2"

    skills = {path.parent.name for path in (output / "skills").glob("*/SKILL.md")}
    assert skills == PACKAGED_SKILLS
    assert (output / "scripts" / "start_mcp_server.py").is_file()
    assert (output / "scripts" / "start_hpc_broker.py").is_file()
    assert (output / "runtime" / "simflow_core").is_dir()
    assert (output / "mcp" / "servers").is_dir()

    for forbidden in [
        "tests",
        ".simflow",
        ".omx",
        ".codex-plugin",
        ".claude-plugin",
        ".mcp.json",
        ".claude.mcp.json",
    ]:
        assert not (output / forbidden).exists()
    assert [path for path in output.rglob("*") if path.name in RESTRICTED_NAMES] == []


def test_opencode_validator_accepts_built_package(tmp_path):
    output = tmp_path / "opencode-plugin"
    subprocess.run(
        ["node", "scripts/build_opencode_plugin.js", str(output)],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        ["node", "scripts/validate_opencode_plugin.js"],
        cwd=ROOT,
        env={**os.environ, "SIMFLOW_OPENCODE_PLUGIN_ROOT": str(output)},
        check=True,
    )


def test_opencode_tarball_resolves_server_export(tmp_path):
    output = tmp_path / "opencode-plugin"
    pack_dir = tmp_path / "pack"
    install_dir = tmp_path / "install"
    cache_dir = tmp_path / "npm-cache"
    pack_dir.mkdir()
    subprocess.run(
        ["node", "scripts/build_opencode_plugin.js", str(output)],
        cwd=ROOT,
        check=True,
    )
    env = {**os.environ, "npm_config_cache": str(cache_dir)}
    subprocess.run(
        ["npm", "pack", "--pack-destination", str(pack_dir)],
        cwd=output,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    version = read_json(ROOT / "package.json")["version"]
    tarball = pack_dir / f"opencode-simflow-{version}.tgz"
    assert tarball.is_file()
    subprocess.run(
        [
            "npm",
            "install",
            "--prefix",
            str(install_dir),
            str(tarball),
            "--ignore-scripts",
            "--no-audit",
            "--no-fund",
        ],
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    result = subprocess.run(
        [
            "node",
            "--input-type=module",
            "-e",
            "import('opencode-simflow/server').then((m) => console.log(m.default.id))",
        ],
        cwd=install_dir,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "simflow"
