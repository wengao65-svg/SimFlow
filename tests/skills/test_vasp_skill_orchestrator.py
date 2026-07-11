#!/usr/bin/env python3
"""Tests for simflow-vasp orchestration skill script."""

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "skills" / "simflow-vasp" / "scripts" / "orchestrate_vasp_task.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("orchestrate_vasp_task", str(SCRIPT))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_inputs(base: Path, incar: str):
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
    (base / "INCAR").write_text(incar, encoding="utf-8")
    (base / "KPOINTS").write_text("mesh\n0\nGamma\n4 4 4\n0 0 0\n", encoding="utf-8")
    (base / "POTCAR").write_text("PAW_PBE Si 05Jan2001\n POMASS = 1; ZVAL = 4.0\n", encoding="utf-8")


def _run_cli(*args: str) -> dict:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(completed.stdout)


def test_orchestrator_relax_static_dos_aimd_reports():
    module = _load_module()
    for task in ["relax", "static", "dos", "aimd"]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            incar = "IBRION = 0\nNSW = 10\n" if task == "aimd" else "IBRION = -1\nNSW = 0\n"
            _write_inputs(root, incar)
            result = module.orchestrate_vasp_task(task, str(root))
            assert result["status"] == "success"
            assert result["simflow_result"]["role"] == "helper"
            assert result["simflow_result"]["activity"] == "orchestration"
            assert result["simflow_result"]["stage"] == "computation"
            assert result["simflow_result"]["state_effect"] == "none"
            assert (root / "reports/vasp/input_manifest.json").is_file()
            assert (root / "reports/vasp/validation_report.json").is_file()
            assert (root / "reports/vasp/compute_plan.json").is_file()
            assert (root / "reports/vasp/analysis_report.json").is_file()
            assert (root / "reports/vasp/handoff_artifact.json").is_file()
            assert not (root / ".simflow").exists()


def test_orchestrator_neb_basic_reports_even_when_validation_fails():
    module = _load_module()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_inputs(root, "IBRION = 3\nNSW = 20\n")
        result = module.orchestrate_vasp_task("neb", str(root))
        validation = json.loads((root / "reports/vasp/validation_report.json").read_text())
        assert result["status"] == "success"
        assert validation["status"] == "fail"
        assert result["simflow_result"]["state_effect"] == "none"
        assert "artifacts" not in result["written"]
        assert "checkpoint" not in result["written"]
        assert not (root / ".simflow").exists()


def test_orchestrator_unknown_phonon_task_writes_uncertainty_manifest():
    module = _load_module()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_inputs(root, "IBRION = -1\nNSW = 0\n")
        result = module.orchestrate_vasp_task("phonon finite displacement", str(root))
        manifest = json.loads((root / "reports/vasp/input_manifest.json").read_text(encoding="utf-8"))

        assert result["status"] == "success"
        assert result["plan"]["task"] == "unknown"
        assert manifest["classification_status"] == "needs_clarification"
        assert manifest["candidates"]
        assert result["simflow_result"]["stage"] == "computation"
        assert not (root / ".simflow").exists()


def test_orchestrator_help_describes_reports_dir_and_explicit_helper_recording():
    module = _load_module()
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        check=False,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0
    assert "reports/vasp" in module.__doc__
    assert "reports/vasp" in completed.stdout
    assert "explicit helper-run recording" in completed.stdout.lower()
    assert "writes .simflow and reports" not in completed.stdout.lower()
    assert "writes reports and simflow state only" not in module.__doc__.lower()


def test_orchestrator_preserves_existing_omx_without_initializing_simflow():
    module = _load_module()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        omx = root / ".omx"
        omx.mkdir()
        host_file = omx / "simflow_status_summary.md"
        host_file.write_text("host session\n", encoding="utf-8")
        _write_inputs(root, "IBRION = -1\nNSW = 0\n")

        result = module.orchestrate_vasp_task("relax", str(root))

        assert result["status"] == "success"
        assert not (root / ".simflow").exists()
        assert (root / "reports/vasp/input_manifest.json").is_file()
        assert host_file.read_text(encoding="utf-8") == "host session\n"
        for report in (root / "reports/vasp").glob("*.json"):
            json.loads(report.read_text(encoding="utf-8"))


def test_orchestrator_record_helper_run_creates_helper_artifacts_without_stage_or_checkpoint_mutation():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_inputs(root, "IBRION = -1\nNSW = 0\n")

        result = _run_cli(
            "--task",
            "relax",
            "--project-root",
            str(root),
            "--record-helper-run",
        )

        assert result["status"] == "success"
        assert result["simflow_result"]["state_effect"] == "record_only"
        assert result["helper_run_id"].startswith("helper_")
        assert result["helper_run_manifest_artifact_id"].startswith("art_")

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


@pytest.mark.parametrize("inline_value", [False, True])
def test_orchestrator_recording_redacts_sensitive_values_inside_options(tmp_path, inline_value):
    _write_inputs(tmp_path, "IBRION = -1\nNSW = 0\n")
    private_root = "/licensed/private/potpaw_PBE"
    private_token = "private-token-value"
    options = json.dumps({"potcar_root": private_root, "service_token": private_token})
    options_args = [f"--options={options}"] if inline_value else ["--options", options]

    result = _run_cli(
        "--task",
        "relax",
        "--project-root",
        str(tmp_path),
        *options_args,
        "--record-helper-run",
    )

    serialized = json.dumps(result)
    recorded_json = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (tmp_path / ".simflow").rglob("*.json")
    )
    assert private_root not in serialized
    assert private_token not in serialized
    assert private_root not in recorded_json
    assert private_token not in recorded_json
    assert "<redacted>" in recorded_json


@pytest.mark.parametrize("calc_dir_factory", [lambda root: "../outside", lambda root: str(root.parent / "outside-abs")])
def test_orchestrator_rejects_calc_dir_outside_project_root(calc_dir_factory):
    module = _load_module()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_inputs(root, "IBRION = -1\nNSW = 0\n")
        outside = root.parent / "outside-abs"

        with pytest.raises(ValueError, match="project_root|project root|boundary"):
            module.orchestrate_vasp_task("relax", str(root), calc_dir=calc_dir_factory(root))

        assert not outside.exists()
        assert not (root.parent / "outside").exists()


def test_troubleshoot_no_fetch_has_official_sources():
    from runtime.simflow_helpers.engines.vasp_lookup import summarize_troubleshooting

    result = summarize_troubleshooting("NBANDS", fetch=False)
    urls = [item["url"] for item in result["sources"]]
    assert any("vasp.at/wiki" in url for url in urls)
    assert any("vasp.at/py4vasp" in url for url in urls)
