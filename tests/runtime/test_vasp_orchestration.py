#!/usr/bin/env python3
"""Tests for VASP orchestration adapters."""

import json
import sys
import tempfile
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "runtime"))

from lib.state import init_workflow
from lib.vasp_py4vasp import can_use_py4vasp, read_with_py4vasp
from lib.vasp_tools import detect_vaspkit, plan_vaspkit_task, run_vaspkit_safe
from lib.vasp_validation import validate_potcar_metadata, validate_vasp_inputs
from lib.vasp_workflows import build_vasp_task_plan, classify_vasp_request, write_vasp_artifacts


def _write_basic_inputs(base: Path, kpoints_mode: str = "mesh", potcar_order: str = "Si"):
    (base / "POSCAR").write_text(
        """Si
1.0
  5 0 0
  0 5 0
  0 0 5
Si
2
Direct
  0 0 0
  0.25 0.25 0.25
""",
        encoding="utf-8",
    )
    (base / "INCAR").write_text("NSW = 0\nIBRION = -1\n", encoding="utf-8")
    if kpoints_mode == "line":
        (base / "KPOINTS").write_text("line\n10\nLine-mode\nreciprocal\n0 0 0\n0.5 0 0\n", encoding="utf-8")
    else:
        (base / "KPOINTS").write_text("mesh\n0\nGamma\n4 4 4\n0 0 0\n", encoding="utf-8")
    (base / "POTCAR").write_text(f"PAW_PBE {potcar_order} 05Jan2001\n POMASS = 1; ZVAL = 4.0\n", encoding="utf-8")


def test_classify_common_tasks():
    result = classify_vasp_request("run band structure after scf", ["POSCAR", "INCAR", "KPOINTS"])
    assert result["task"] == "band"
    assert "CHGCAR" in result["missing_inputs"]
    assert "static SCF with CHGCAR" in result["predecessors"]


def test_vaspkit_missing_fallback_plan(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: None)
    detected = detect_vaspkit()
    plan = plan_vaspkit_task("band", "/tmp/example")
    dry = run_vaspkit_safe(plan)
    assert detected["available"] is False
    assert plan["available"] is False
    assert dry["status"] == "dry_run"


def test_potcar_metadata_does_not_include_content(tmp_path):
    _write_basic_inputs(tmp_path)
    result = validate_potcar_metadata(str(tmp_path / "POSCAR"), str(tmp_path / "POTCAR"))
    assert result["valid"] is True
    assert result["content_included"] is False
    assert "PAW_PBE" not in json.dumps(result)


def test_band_requires_chgcar_and_line_kpoints(tmp_path):
    _write_basic_inputs(tmp_path, kpoints_mode="mesh")
    result = validate_vasp_inputs("band", str(tmp_path))
    checks = {c["check"]: c for c in result["checks"]}
    assert result["status"] == "fail"
    assert checks["prior_scf_chgcar"]["passed"] is False
    assert checks["kpoints_task_match"]["passed"] is False


def test_py4vasp_preferred_when_h5_exists(monkeypatch, tmp_path):
    (tmp_path / "vaspout.h5").write_text("fake", encoding="utf-8")

    fake_module = types.SimpleNamespace(
        __version__="test",
        Calculation=types.SimpleNamespace(
            from_path=lambda path: types.SimpleNamespace(
                energy=types.SimpleNamespace(read=lambda: {"free_energy": [-1.0]}),
                structure=object(),
            )
        ),
    )
    monkeypatch.setattr("importlib.util.find_spec", lambda name: object() if name == "py4vasp" else None)
    monkeypatch.setattr("importlib.import_module", lambda name: fake_module if name == "py4vasp" else __import__(name))

    assert can_use_py4vasp(str(tmp_path))["usable"] is True
    result = read_with_py4vasp(str(tmp_path), "energy")
    assert result["status"] == "success"
    assert result["backend"] == "py4vasp"


def test_workflow_writes_artifacts_checkpoint_and_blocks_submit(tmp_path):
    _write_basic_inputs(tmp_path)
    init_workflow("dft", "input_generation", str(tmp_path))
    plan = build_vasp_task_plan("relax", str(tmp_path), {"calc_dir": "."})
    written = write_vasp_artifacts(plan, str(tmp_path), workflow_id="wf_test")

    assert (tmp_path / "reports/vasp/input_manifest.json").is_file()
    assert (tmp_path / "reports/vasp/validation_report.json").is_file()
    assert (tmp_path / ".simflow/state/artifacts.json").is_file()
    assert written["checkpoint"]["checkpoint_id"].startswith("ckpt_")
    compute_plan = json.loads((tmp_path / "reports/vasp/compute_plan.json").read_text())
    assert compute_plan["dry_run"] is True
    assert compute_plan["real_submit"] is False


def test_hpc_gate_blocks_incomplete_realistic_plan(tmp_path):
    _write_basic_inputs(tmp_path)
    plan = build_vasp_task_plan("dos", str(tmp_path), {"calc_dir": "."})
    gate = plan["compute_plan"]["hpc_submit_gate"]
    assert gate["status"] == "block"
    assert "input_files_complete" in gate["conditions"]["unmet"]


def test_surface_adsorption_defect_checks_are_poscar_scoped(tmp_path):
    _write_basic_inputs(tmp_path)
    for extra in ("INCAR", "KPOINTS", "POTCAR"):
        (tmp_path / extra).unlink()

    surface = validate_vasp_inputs("surface_check", str(tmp_path))
    adsorption = validate_vasp_inputs("adsorption_check", str(tmp_path))
    defect = validate_vasp_inputs("defect_check", str(tmp_path))

    assert any(c["check"] == "surface_vacuum_heuristic" for c in surface["checks"])
    assert any(c["check"] == "adsorption_species_diversity" for c in adsorption["checks"])
    assert defect["status"] in {"pass", "fail"}
    assert not any(c["check"] == "incar_exists" for c in surface["checks"])
