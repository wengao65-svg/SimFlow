"""Installed Skills carry their own runnable Python helpers and local resources."""

import os
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_all_three_packages_carry_standalone_helpers(tmp_path):
    builders = [
        ("build_marketplace_wrapper.js", "plugins/simflow"),
        ("build_claude_marketplace_wrapper.js", "plugins/simflow"),
        ("build_opencode_plugin.js", ""),
    ]
    source_skills = ROOT / "skills"
    for index, (builder, suffix) in enumerate(builders):
        target = tmp_path / f"package-{index}"
        subprocess.run(["node", str(ROOT / "scripts" / builder), str(target)], cwd=ROOT, check=True, capture_output=True)
        package = target / suffix
        assert not any((package / name).exists() for name in ("runtime", "mcp", "workflow", "schemas"))
        for source_skill in source_skills.glob("*/SKILL.md"):
            skill_dir = source_skill.parent
            if skill_dir.name == "simflow":
                continue
            installed = package / "skills" / skill_dir.name
            for kind in ("scripts", "lib", "assets"):
                source = skill_dir / kind
                if source.exists():
                    assert (installed / kind).is_dir()
                    assert sorted(path.name for path in source.iterdir() if path.is_file() and path.suffix != ".pyc") == sorted(
                        path.name for path in (installed / kind).iterdir() if path.is_file() and path.suffix != ".pyc"
                    )
            for script in (installed / "scripts").glob("[!_]*.py"):
                env = dict(os.environ)
                env.pop("PYTHONPATH", None)
                completed = subprocess.run(
                    [sys.executable, str(script), "--help"], cwd=tmp_path,
                    env=env, text=True, capture_output=True,
                )
                assert completed.returncode == 0, f"{script}: {completed.stderr or completed.stdout}"

        # Exercise generated scientific content outside the source checkout.
        installed_skills = package / "skills"
        model = installed_skills / "simflow-modeling"
        assert (model / "requirements.txt").is_file()
        output = tmp_path / f"fcc-{index}.cif"
        subprocess.run([sys.executable, str(model / "scripts/build_structure.py"),
                        "from_type", "--type", "fcc", "--elements", "Al",
                        "--lattice-param", "4", "--format", "cif", "--output", str(output)],
                       cwd=tmp_path, env=env, check=True, capture_output=True, text=True)
        from ase.io import read
        assert len(read(output)) == 4
        calc = tmp_path / f"cp2k-{index}"
        subprocess.run([sys.executable, str(installed_skills / "simflow-cp2k/scripts/generate_cp2k_inputs.py"),
                        "--structure", str(output), "--task", "energy", "--output-dir", str(calc)],
                       cwd=tmp_path, env=env, check=True, capture_output=True, text=True)
        assert len(read(calc / "structure.xyz")) == 4
        parsed = subprocess.run([sys.executable, str(installed_skills / "simflow-vasp/scripts/validate_vasp_outputs.py"),
                                 "--outcar", str(ROOT / "tests/fixtures/OUTCAR_convergence_synthetic")],
                                cwd=tmp_path, env=env, check=True, capture_output=True, text=True)
        assert json.loads(parsed.stdout)["status"] == "pass"
        assert not (tmp_path / ".simflow").exists()
