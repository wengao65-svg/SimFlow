#!/usr/bin/env python3
"""Tests for simflow-vasp orchestration skill script."""

import importlib.util
import json
import tempfile
from pathlib import Path


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


def test_orchestrator_relax_static_dos_aimd_reports():
    module = _load_module()
    for task in ["relax", "static", "dos", "aimd"]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            incar = "IBRION = 0\nNSW = 10\n" if task == "aimd" else "IBRION = -1\nNSW = 0\n"
            _write_inputs(root, incar)
            result = module.orchestrate_vasp_task(task, str(root))
            assert result["status"] == "success"
            assert (root / "reports/vasp/input_manifest.json").is_file()
            assert (root / "reports/vasp/validation_report.json").is_file()
            assert (root / "reports/vasp/compute_plan.json").is_file()
            assert (root / "reports/vasp/analysis_report.json").is_file()
            assert (root / "reports/vasp/handoff_artifact.json").is_file()


def test_orchestrator_neb_basic_artifacts_even_when_validation_fails():
    module = _load_module()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_inputs(root, "IBRION = 3\nNSW = 20\n")
        result = module.orchestrate_vasp_task("neb", str(root))
        validation = json.loads((root / "reports/vasp/validation_report.json").read_text())
        assert result["status"] == "success"
        assert validation["status"] == "fail"
        assert (root / ".simflow/checkpoints").is_dir()


def test_orchestrator_initializes_project_with_existing_omx():
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
        assert (root / ".simflow/state/workflow.json").is_file()
        assert (root / ".simflow/state/artifacts.json").is_file()
        assert (root / ".simflow/state/checkpoints.json").is_file()
        assert (root / "reports/vasp/input_manifest.json").is_file()
        assert host_file.read_text(encoding="utf-8") == "host session\n"
        for report in (root / "reports/vasp").glob("*.json"):
            json.loads(report.read_text(encoding="utf-8"))


def test_troubleshoot_no_fetch_has_official_sources():
    from runtime.lib.vasp_lookup import summarize_troubleshooting

    result = summarize_troubleshooting("NBANDS", fetch=False)
    urls = [item["url"] for item in result["sources"]]
    assert any("vasp.at/wiki" in url for url in urls)
    assert any("vasp.at/py4vasp" in url for url in urls)
