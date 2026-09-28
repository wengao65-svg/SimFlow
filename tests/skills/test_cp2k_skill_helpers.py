"""End-to-end checks for the independent CP2K Skill helpers."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills" / "simflow-cp2k" / "scripts"
FIXTURES = ROOT / "tests" / "fixtures" / "cp2k"


def _run(script: str, *args: str) -> dict:
    completed = subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        cwd=ROOT, text=True, capture_output=True, check=True,
    )
    return json.loads(completed.stdout)


def test_cp2k_generation_and_validation_are_stateless(tmp_path: Path) -> None:
    structure = tmp_path / "water.xyz"
    structure.write_text("3\nwater\nO 0 0 0\nH 0.7 0.5 0\nH -0.7 0.5 0\n", encoding="utf-8")
    calc = tmp_path / "calc"
    generated = _run("generate_cp2k_inputs.py", "--structure", str(structure), "--task", "energy", "--output-dir", str(calc))
    assert generated["status"] == "success"
    assert (calc / "energy.inp").is_file()
    assert (calc / "last_frame.xyz").is_file()
    checked = _run("validate_cp2k_inputs.py", "--task", "energy", "--calc-dir", str(calc))
    assert checked["status"] == "pass"
    assert not (tmp_path / ".simflow").exists()
    assert not (tmp_path / "reports").exists()


def test_cp2k_parser_reads_existing_outputs_without_writing(tmp_path: Path) -> None:
    calc = tmp_path / "calc"
    calc.mkdir()
    for source in FIXTURES.iterdir():
        shutil.copy2(source, calc / source.name)
    result = _run("parse_cp2k_outputs.py", "--calc-dir", str(calc), "--project", "md")
    assert result["status"] == "parsed"
    assert result["summary"]["md_steps"] > 0
    assert result["summary"]["final_energy"] is not None
    assert not (tmp_path / ".simflow").exists()
    assert not (tmp_path / "reports").exists()


def test_cp2k_generation_refuses_overwrite_and_parent_path(tmp_path: Path) -> None:
    structure = tmp_path / "water.xyz"
    structure.write_text("1\nwater\nO 0 0 0\n", encoding="utf-8")
    calc = tmp_path / "calc"
    args = [sys.executable, str(SCRIPTS / "generate_cp2k_inputs.py"), "--structure", str(structure),
            "--task", "energy", "--output-dir", str(calc)]
    subprocess.run(args, cwd=ROOT, check=True, capture_output=True, text=True)
    original = (calc / "energy.inp").read_bytes()
    blocked = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    assert blocked.returncode != 0
    assert "overwrite" in blocked.stderr
    assert (calc / "energy.inp").read_bytes() == original
    unsafe = subprocess.run([*args, "--params", '{"coord_file":"../outside.xyz"}'], cwd=ROOT, capture_output=True, text=True)
    assert unsafe.returncode != 0
    assert not (tmp_path / "outside.xyz").exists()


def test_cif_preserves_nonorthogonal_cell_and_symmetry(tmp_path):
    import numpy as np
    from ase.io import read
    cif = tmp_path / "hexagonal.cif"
    cif.write_text("""data_test
_cell_length_a 4
_cell_length_b 4
_cell_length_c 6
_cell_angle_alpha 90
_cell_angle_beta 90
_cell_angle_gamma 120
_space_group_name_H-M_alt 'P -1'
loop_
_space_group_symop_operation_xyz
'x,y,z'
'-x,-y,-z'
loop_
_atom_site_label
_atom_site_type_symbol
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
Si1 Si 0.1 0.2 0.3
""")
    calc = tmp_path / "calc"
    _run("generate_cp2k_inputs.py", "--structure", str(cif), "--task", "energy", "--output-dir", str(calc))
    lines = (calc / "energy.inp").read_text().splitlines()
    vectors = [[float(x) for x in line.split()[1:]] for line in lines if line.split() and line.split()[0] in ("A", "B", "C")]
    original = read(cif)
    generated = read(calc / "structure.xyz")
    assert len(generated) == 2
    assert np.allclose(vectors, original.cell)
    assert np.allclose(generated.positions, original.positions)
    assert _run("validate_cp2k_inputs.py", "--task", "energy", "--calc-dir", str(calc))["status"] == "pass"
