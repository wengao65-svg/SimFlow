"""Check the independent VASP Skill's scientific and restricted-file boundaries."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills" / "simflow-vasp" / "scripts" / "generate_vasp_inputs.py"
POSCAR = ROOT / "tests" / "fixtures" / "POSCAR_Si"


def test_vasp_generator_writes_only_calculation_inputs(tmp_path: Path) -> None:
    calc = tmp_path / "calc"
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--poscar", str(POSCAR), "--job-type", "scf", "--output-dir", str(calc), "--kppa", "100"],
        cwd=ROOT, text=True, capture_output=True, check=True,
    )
    result = json.loads(completed.stdout)
    assert result["status"] == "success"
    assert (calc / "INCAR").is_file()
    assert (calc / "KPOINTS").is_file()
    assert (calc / "POSCAR").is_file()
    assert not (tmp_path / ".simflow").exists()
    assert not (tmp_path / "reports").exists()
    assert "simflow_result" not in result


def test_vasp_generator_never_emits_licensed_potcar_content(tmp_path: Path) -> None:
    library = tmp_path / "private" / "PBE" / "Si"
    library.mkdir(parents=True)
    (library / "POTCAR").write_text("PAW_PBE Si 05Jan2001\nPOMASS = 1.0; ZVAL = 4.0\nPRIVATE_MARKER\n", encoding="utf-8")
    calc = tmp_path / "calc"
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--poscar", str(POSCAR), "--job-type", "scf", "--output-dir", str(calc),
         "--kppa", "100", "--potcar-root", str(tmp_path / "private")],
        cwd=ROOT, text=True, capture_output=True, check=True,
    )
    result = json.loads(completed.stdout)
    assert result["potcar"]["status"] == "materialized"
    assert (calc / "POTCAR").is_file()
    assert "PRIVATE_MARKER" not in completed.stdout
    assert str(tmp_path / "private") not in completed.stdout
    assert not (tmp_path / ".simflow").exists()


def test_vasp_generator_refuses_existing_inputs_and_report_redacts_library(tmp_path: Path) -> None:
    library = tmp_path / "private" / "PBE" / "Si"
    library.mkdir(parents=True)
    (library / "POTCAR").write_text("PAW_PBE Si 05Jan2001\nPOMASS = 1.0; ZVAL = 4.0\nPRIVATE_MARKER\n")
    calc = tmp_path / "calc"
    report = tmp_path / "report.json"
    command = [sys.executable, str(SCRIPT), "--poscar", str(POSCAR), "--job-type", "scf",
               "--output-dir", str(calc), "--kppa", "100", "--potcar-root", str(tmp_path / "private")]
    subprocess.run([*command, "--report", str(report)], cwd=ROOT, check=True, capture_output=True, text=True)
    report_text = report.read_text()
    assert "PRIVATE_MARKER" not in report_text
    assert str(tmp_path / "private") not in report_text
    original = (calc / "INCAR").read_bytes()
    blocked = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    assert blocked.returncode != 0
    assert "overwrite" in blocked.stdout
    assert (calc / "INCAR").read_bytes() == original


def test_output_validation_separates_scf_ionic_forces_and_termination(tmp_path):
    validator = SCRIPT.parent / "validate_vasp_outputs.py"
    outcar = tmp_path / "OUTCAR"

    def check(content, tolerance="0.01"):
        outcar.write_text(content)
        completed = subprocess.run([sys.executable, str(validator), "--outcar", str(outcar),
                                    "--force-tol", tolerance], check=True, text=True, capture_output=True)
        return json.loads(completed.stdout)

    static = "NSW = 0\naborting loop because EDIFF is reached\nenergy(sigma->0) = -12\n"
    assert check(static)["status"] == "fail"  # no termination evidence
    assert check(static + "General timing and accounting\n")["status"] == "pass"
    relax = ("NSW = 10\naborting loop because EDIFF is reached\n"
             "reached required accuracy\nFORCES: max atom, RMS 0.05 0.01\n"
             "General timing and accounting\n")
    assert check(relax)["status"] == "fail"
    assert check(relax, "0.1")["status"] == "pass"
    assert check(relax.replace("FORCES: max atom, RMS 0.05 0.01\n", ""))["status"] == "unknown"
    assert check(relax.replace("aborting loop because EDIFF is reached\n", ""))["status"] == "fail"
