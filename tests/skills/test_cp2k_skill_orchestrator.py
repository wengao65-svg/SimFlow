#!/usr/bin/env python3
"""Tests for the simflow-cp2k orchestrator wrapper."""

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills" / "simflow-cp2k" / "scripts" / "orchestrate_cp2k_task.py"
GENERATE_SCRIPT = ROOT / "skills" / "simflow-cp2k" / "scripts" / "generate_cp2k_inputs.py"
VALIDATE_SCRIPT = ROOT / "skills" / "simflow-cp2k" / "scripts" / "validate_cp2k_inputs.py"
PARSE_SCRIPT = ROOT / "skills" / "simflow-cp2k" / "scripts" / "parse_cp2k_outputs.py"
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "cp2k"


def _load_module():
    spec = importlib.util.spec_from_file_location("orchestrate_cp2k_task", str(SCRIPT))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_script_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_script(path: Path, *args: str) -> dict:
    completed = subprocess.run(
        [sys.executable, str(path), *args],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(completed.stdout)


def _write_inputs(base: Path):
    (base / "structure.xyz").write_text(
        "3\nwater\nO 0 0 0\nH 0.7 0.5 0\nH -0.7 0.5 0\n",
        encoding="utf-8",
    )
    (base / "energy.inp").write_text(
        """&GLOBAL
  PROJECT test_energy
  RUN_TYPE ENERGY
  PRINT_LEVEL LOW
&END GLOBAL

&FORCE_EVAL
  METHOD QS
  &DFT
    BASIS_SET_FILE_NAME BASIS_MOLOPT
    POTENTIAL_FILE_NAME POTENTIAL
    CHARGE 0
    MULTIPLICITY 1
    &QS
      EPS_DEFAULT 1e-08
    &END QS
    &MGRID
      CUTOFF 400
      REL_CUTOFF 50
    &END MGRID
    &SCF
      MAX_SCF 50
      EPS_SCF 1e-06
      SCF_GUESS ATOMIC
      &OT ON
        MINIMIZER DIIS
        PRECONDITIONER FULL_SINGLE_INVERSE
      &END OT
      &OUTER_SCF
        MAX_SCF 20
        EPS_SCF 1e-06
      &END OUTER_SCF
      &PRINT
        &RESTART OFF
        &END RESTART
      &END PRINT
    &END SCF
    &XC
      &XC_FUNCTIONAL PBE
      &END XC_FUNCTIONAL
    &END XC
  &END DFT
  &SUBSYS
    &CELL
      ABC 10 10 10
      PERIODIC XYZ
    &END CELL
    &TOPOLOGY
      COORD_FILE_NAME structure.xyz
      COORD_FILE_FORMAT XYZ
    &END TOPOLOGY
    &KIND O
      BASIS_SET DZVP-MOLOPT-SR-GTH
      POTENTIAL GTH-PBE-q6
    &END KIND
    &KIND H
      BASIS_SET DZVP-MOLOPT-SR-GTH
      POTENTIAL GTH-PBE-q1
    &END KIND
  &END SUBSYS
&END FORCE_EVAL
""",
        encoding="utf-8",
    )


def test_orchestrator_writes_reports_without_default_simflow_state(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: None)
    module = _load_module()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_inputs(root)
        result = module.orchestrate_cp2k_task("energy", str(root))

        assert result["status"] == "success"
        assert result["simflow_result"]["role"] == "helper"
        assert result["simflow_result"]["activity"] == "orchestration"
        assert result["simflow_result"]["stage"] == "computation"
        assert result["simflow_result"]["state_effect"] == "none"
        assert (root / "reports/cp2k/input_manifest.json").is_file()
        assert (root / "reports/cp2k/validation_report.json").is_file()
        assert (root / "reports/cp2k/compute_plan.json").is_file()
        assert (root / "reports/cp2k/analysis_report.json").is_file()
        assert (root / "reports/cp2k/handoff_artifact.json").is_file()
        assert not (root / ".simflow").exists()
        for report in (root / "reports/cp2k").glob("*.json"):
            json.loads(report.read_text(encoding="utf-8"))


def test_orchestrator_does_not_return_artifacts_or_checkpoint(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: None)
    module = _load_module()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_inputs(root)
        result = module.orchestrate_cp2k_task("energy", str(root))

        assert "artifacts" not in result
        assert "checkpoint" not in result
        assert not (root / ".simflow").exists()


def test_project_root_is_not_plugin_root(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: None)
    module = _load_module()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_inputs(root)
        result = module.orchestrate_cp2k_task("energy", str(root))
        plugin_root = SCRIPT.parents[3].resolve()

        assert root.resolve() != plugin_root
        assert result["reports"]["input_manifest"] == "reports/cp2k/input_manifest.json"
        assert not (plugin_root / "reports" / "cp2k" / "input_manifest.json").exists()


def test_orchestrator_without_local_cp2k_binary_still_plans(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: None)
    module = _load_module()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_inputs(root)
        result = module.orchestrate_cp2k_task("energy", str(root))
        compute_plan = json.loads((root / "reports/cp2k/compute_plan.json").read_text(encoding="utf-8"))

        assert compute_plan["dry_run"] is True
        assert compute_plan["real_submit_allowed"] is False
        assert compute_plan["runtime_detection"]["detected"] is False


def test_orchestrator_unknown_task_writes_uncertainty_manifest(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: None)
    module = _load_module()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "structure.xyz").write_text("1\ncustom\nSi 0 0 0\n", encoding="utf-8")
        result = module.orchestrate_cp2k_task("custom phonon workflow", str(root))
        manifest = json.loads((root / "reports/cp2k/input_manifest.json").read_text(encoding="utf-8"))

        assert result["status"] == "success"
        assert result["task"] == "unknown"
        assert manifest["classification_status"] == "needs_clarification"
        assert manifest["candidates"]
        assert result["simflow_result"]["stage"] == "computation"
        assert not (root / ".simflow").exists()


def test_orchestrator_parses_outputs_when_present(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: None)
    module = _load_module()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_inputs(root)
        for name in ("md.log", "md.ener", "md-pos-1.xyz", "md.restart"):
            (root / name).write_text((FIXTURE_DIR / name).read_text(encoding="utf-8"), encoding="utf-8")

        result = module.orchestrate_cp2k_task("troubleshoot", str(root))
        analysis = json.loads((root / "reports/cp2k/analysis_report.json").read_text(encoding="utf-8"))

        assert result["status"] == "success"
        assert analysis["status"] == "parsed"
        assert analysis["summary"]["final_energy"] == -17.05


@pytest.mark.parametrize(
    ("request_text", "expected_task"),
    [
        ("please parse cp2k outputs", "parse"),
        ("please troubleshoot cp2k outputs", "troubleshoot"),
    ],
)
def test_orchestrator_derives_stage_from_phrase_classified_task(monkeypatch, request_text, expected_task):
    monkeypatch.setattr("shutil.which", lambda name: None)
    module = _load_module()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_inputs(root)
        for name in ("md.log", "md.ener", "md-pos-1.xyz", "md.restart"):
            (root / name).write_text((FIXTURE_DIR / name).read_text(encoding="utf-8"), encoding="utf-8")

        result = module.orchestrate_cp2k_task(request_text, str(root))

        assert result["status"] == "success"
        assert result["task"] == expected_task
        assert result["plan"]["task"] == expected_task
        assert result["simflow_result"]["stage"] == "analysis_visualization"
        assert result["simflow_result"]["state_effect"] == "none"


def test_cp2k_generation_wrapper_records_computation_stage():
    module = _load_script_module("cp2k_generate_wrapper", GENERATE_SCRIPT)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "structure.xyz").write_text(
            "3\nwater\nO 0 0 0\nH 0.7 0.5 0\nH -0.7 0.5 0\n",
            encoding="utf-8",
        )

        result = module.generate_cp2k_inputs(str(root / "structure.xyz"), "energy", str(root))

        assert result["status"] == "success"
        assert result["simflow_result"]["role"] == "helper"
        assert result["simflow_result"]["activity"] == "input_generation"
        assert result["simflow_result"]["stage"] == "computation"
        assert result["simflow_result"]["state_effect"] == "none"
        assert "artifacts" not in result
        assert "checkpoint" not in result
        assert not (root / ".simflow").exists()


def test_cp2k_validation_wrapper_records_computation_stage():
    generate = _load_script_module("cp2k_generate_wrapper_for_validation", GENERATE_SCRIPT)
    validate = _load_script_module("cp2k_validate_wrapper", VALIDATE_SCRIPT)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "structure.xyz").write_text(
            "3\nwater\nO 0 0 0\nH 0.7 0.5 0\nH -0.7 0.5 0\n",
            encoding="utf-8",
        )
        generate.generate_cp2k_inputs(str(root / "structure.xyz"), "energy", str(root))

        result = validate.run_validation("energy", str(root), input_path="energy.inp")

        assert result["status"] == "success"
        assert result["simflow_result"]["activity"] == "input_validation"
        assert result["simflow_result"]["stage"] == "computation"
        assert result["simflow_result"]["state_effect"] == "none"
        assert "artifacts" not in result
        assert "checkpoint" not in result
        assert not (root / ".simflow").exists()


def test_cp2k_parse_wrapper_records_analysis_visualization_stage():
    module = _load_script_module("cp2k_parse_wrapper", PARSE_SCRIPT)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        result = module.parse_cp2k_outputs(str(root))

        assert result["status"] == "success"
        assert result["simflow_result"]["activity"] == "analysis"
        assert result["simflow_result"]["stage"] == "analysis_visualization"
        assert result["simflow_result"]["state_effect"] == "none"
        assert "artifacts" not in result
        assert "checkpoint" not in result
        assert not (root / ".simflow").exists()


def test_cp2k_record_helper_run_creates_helper_artifacts_only():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_inputs(root)

        result = _run_script(
            SCRIPT,
            "--task",
            "energy",
            "--project-root",
            str(root),
            "--record-helper-run",
        )

        assert result["status"] == "success"
        assert result["simflow_result"]["state_effect"] == "record_only"
        checkpoints = json.loads((root / ".simflow/state/checkpoints.json").read_text(encoding="utf-8"))
        stages = json.loads((root / ".simflow/state/stages.json").read_text(encoding="utf-8"))
        artifacts = json.loads((root / ".simflow/state/artifacts.json").read_text(encoding="utf-8"))
        manifest_path = next(
            Path(root / artifact["path"])
            for artifact in artifacts
            if artifact["type"] == "helper_run_manifest"
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        assert checkpoints == []
        assert stages == {}
        assert manifest["metadata"]["simflow_result"]["state_effect"] == "record_only"
        assert {artifact["type"] for artifact in artifacts} == {
            "helper_script",
            "helper_output",
            "helper_run_manifest",
        }


@pytest.mark.parametrize("calc_dir_factory", [lambda root: "../outside", lambda root: str(root.parent / "outside-abs")])
def test_cp2k_wrappers_reject_calc_dir_outside_project_root(monkeypatch, calc_dir_factory):
    monkeypatch.setattr("shutil.which", lambda name: None)
    orchestrate = _load_module()
    generate = _load_script_module("cp2k_generate_wrapper_boundary", GENERATE_SCRIPT)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_inputs(root)
        outside = root.parent / "outside-abs"

        with pytest.raises(ValueError, match="project_root|project root|boundary"):
            orchestrate.orchestrate_cp2k_task("energy", str(root), calc_dir=calc_dir_factory(root))
        with pytest.raises(ValueError, match="project_root|project root|boundary"):
            generate.generate_cp2k_inputs(str(root / "structure.xyz"), "energy", str(root), calc_dir=calc_dir_factory(root))

        assert not outside.exists()
        assert not (root.parent / "outside").exists()
