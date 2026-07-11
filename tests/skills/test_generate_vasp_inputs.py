#!/usr/bin/env python3
"""Tests for generate_vasp_inputs.py skill scripts."""

import importlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures"
INPUT_GEN_SCRIPT = Path(__file__).resolve().parents[2] / "skills" / "simflow-computation" / "scripts" / "generate_vasp_inputs.py"
VASP_SCRIPT = Path(__file__).resolve().parents[2] / "skills" / "simflow-vasp" / "scripts" / "generate_vasp_inputs.py"

pytestmark = pytest.mark.filterwarnings(
    "ignore:Set OLD_ERROR_HANDLING to false and catch the errors directly\\.:DeprecationWarning"
)


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_input_gen_incar():
    mod = _load_module("input_gen", INPUT_GEN_SCRIPT)
    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, "INCAR")
        mod.generate_incar("scf", {"job_name": "test"}, out)
        content = Path(out).read_text()
        assert "SYSTEM = test" in content
        assert "NSW" in content


def test_input_gen_kpoints():
    mod = _load_module("input_gen", INPUT_GEN_SCRIPT)
    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, "KPOINTS")
        mod.generate_kpoints({"kx": 4, "ky": 4, "kz": 4}, out)
        content = Path(out).read_text()
        assert "4" in content


def test_input_gen_relax_params():
    mod = _load_module("input_gen", INPUT_GEN_SCRIPT)
    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, "INCAR")
        mod.generate_incar("relax", {}, out)
        content = Path(out).read_text()
        assert "IBRION" in content
        assert "NSW" in content


def test_vasp_pymatgen_inputs():
    mod = _load_module("vasp_gen", VASP_SCRIPT)
    with tempfile.TemporaryDirectory() as tmpdir:
        result = mod.generate_vasp_inputs(
            str(FIXTURE_DIR / "POSCAR_Si"), "scf", tmpdir, kppa=100
        )
        assert result["status"] == "success"
        assert os.path.exists(os.path.join(tmpdir, "INCAR"))
        assert os.path.exists(os.path.join(tmpdir, "KPOINTS"))
        assert os.path.exists(os.path.join(tmpdir, "POSCAR"))
        assert result["num_atoms"] == 2


def test_vasp_generator_function_result_has_default_helper_result_contract():
    mod = _load_module("vasp_gen_result_contract", VASP_SCRIPT)
    with tempfile.TemporaryDirectory() as tmpdir:
        result = mod.generate_vasp_inputs(
            str(FIXTURE_DIR / "POSCAR_Si"), "scf", tmpdir, kppa=100
        )

        assert result["status"] == "success"
        assert result["simflow_result"]["schema_version"] == "simflow.result.v1"
        assert result["simflow_result"]["role"] == "helper"
        assert result["simflow_result"]["activity"] == "vasp_generate_inputs"
        assert result["simflow_result"]["stage"] == "computation"
        assert result["simflow_result"]["state_effect"] == "none"
        assert result["simflow_result"]["outcome"] == "success"


def test_vasp_generator_cli_default_result_has_helper_result_contract(tmp_path):
    completed = subprocess.run(
        [
            sys.executable,
            str(VASP_SCRIPT),
            "--poscar",
            str(FIXTURE_DIR / "POSCAR_Si"),
            "--job-type",
            "scf",
            "--output-dir",
            str(tmp_path / "vasp_input"),
            "--kppa",
            "100",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["status"] == "success"
    assert result["simflow_result"]["role"] == "helper"
    assert result["simflow_result"]["activity"] == "vasp_generate_inputs"
    assert result["simflow_result"]["stage"] == "computation"
    assert result["simflow_result"]["state_effect"] == "none"
    assert not (tmp_path / ".simflow").exists()


def test_vasp_generator_cli_recording_upgrades_helper_result_contract(tmp_path):
    completed = subprocess.run(
        [
            sys.executable,
            str(VASP_SCRIPT),
            "--poscar",
            str(FIXTURE_DIR / "POSCAR_Si"),
            "--job-type",
            "scf",
            "--output-dir",
            str(tmp_path / "vasp_input"),
            "--kppa",
            "100",
            "--project-root",
            str(tmp_path),
            "--record-helper-run",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["status"] == "success"
    assert result["simflow_result"]["role"] == "helper"
    assert result["simflow_result"]["activity"] == "vasp_generate_inputs"
    assert result["simflow_result"]["stage"] == "computation"
    assert result["simflow_result"]["state_effect"] == "record_only"
    assert result["helper_run_id"].startswith("helper_")

    manifests = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in (tmp_path / ".simflow").rglob("*_helper_run.json")
    ]
    assert len(manifests) == 1
    assert manifests[0]["metadata"]["simflow_result"]["state_effect"] == "record_only"


def test_vasp_pymatgen_relax():
    mod = _load_module("vasp_gen", VASP_SCRIPT)
    with tempfile.TemporaryDirectory() as tmpdir:
        result = mod.generate_vasp_inputs(
            str(FIXTURE_DIR / "POSCAR_Si"), "relax", tmpdir, kppa=100
        )
        assert result["status"] == "success"
        incar_content = Path(os.path.join(tmpdir, "INCAR")).read_text()
        assert "NSW" in incar_content


def test_vasp_generator_potcar_compatibility_inputs_are_nonoperative():
    mod = _load_module("vasp_gen_potcar_compat", VASP_SCRIPT)
    with tempfile.TemporaryDirectory() as tmpdir:
        result = mod.generate_vasp_inputs(
            str(FIXTURE_DIR / "POSCAR_Si"),
            "scf",
            tmpdir,
            kppa=100,
            potcar_root="/licensed/potpaw_PBE",
            use_vaspkit=True,
        )
        assert result["status"] == "success"
        assert result["potcar"]["status"] == "metadata_only"
        assert result["potcar"]["content_generated"] is False
        assert "compatibility" in result["potcar"]["message"].lower()
        assert result["potcar"]["compatibility_inputs_ignored"]["potcar_root_supplied"] is True
        assert result["potcar"]["compatibility_inputs_ignored"]["use_vaspkit_supplied"] is True
        serialized = json.dumps(result)
        assert "/licensed/potpaw_PBE" not in serialized
        assert '"potcar_root":' not in serialized
        assert os.path.exists(os.path.join(tmpdir, "POTCAR")) is False
        potcar_info = json.loads(Path(os.path.join(tmpdir, "POTCAR_info.json")).read_text(encoding="utf-8"))
        assert potcar_info["generation"]["compatibility_inputs_ignored"]["potcar_root_supplied"] is True
        serialized_info = json.dumps(potcar_info)
        assert "/licensed/potpaw_PBE" not in serialized_info
        assert '"potcar_root":' not in serialized_info


def test_vasp_generator_does_not_persist_raw_potcar_root_in_stage_payloads():
    mod = _load_module("vasp_gen_potcar_privacy", VASP_SCRIPT)
    with tempfile.TemporaryDirectory() as tmpdir:
        result = mod.generate_vasp_inputs(
            str(FIXTURE_DIR / "POSCAR_Si"),
            "scf",
            tmpdir,
            kppa=100,
            potcar_root="/licensed/private/library",
        )

        assert result["potcar"]["compatibility_inputs_ignored"]["potcar_root_supplied"] is True
        assert result["potcar"]["compatibility_inputs_ignored"]["use_vaspkit_supplied"] is False
        assert "/licensed/private/library" not in json.dumps(result)


@pytest.mark.parametrize("inline_value", [False, True])
def test_vasp_helper_run_redacts_raw_potcar_root_from_recorded_command(tmp_path, inline_value):
    private_root = "/licensed/private/potpaw_PBE"
    potcar_args = (
        [f"--potcar-root={private_root}"]
        if inline_value
        else ["--potcar-root", private_root]
    )
    completed = subprocess.run(
        [
            sys.executable,
            str(VASP_SCRIPT),
            "--poscar",
            str(FIXTURE_DIR / "POSCAR_Si"),
            "--job-type",
            "scf",
            "--output-dir",
            str(tmp_path / "vasp_input"),
            "--kppa",
            "100",
            *potcar_args,
            "--project-root",
            str(tmp_path),
            "--record-helper-run",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert private_root not in completed.stdout
    recorded_json = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (tmp_path / ".simflow").rglob("*.json")
    )
    assert private_root not in recorded_json
    assert "<redacted>" in recorded_json


@pytest.mark.parametrize("inline_value", [False, True])
def test_vasp_helper_run_redacts_sensitive_values_inside_params(tmp_path, inline_value):
    raw_values = [
        "/licensed/private/potpaw_PBE",
        "/licensed/private/single/POTCAR",
        "/licensed/private/env/potpaw_LDA",
        "password-value-123",
        "token-value-123",
        "secret-value-123",
        "api-key-value-123",
        "credential-value-123",
    ]
    params = {
        "ENCUT": 520,
        "potcar_root": raw_values[0],
        "potcar_path": raw_values[1],
        "SIMFLOW_VASP_POTCAR_PATH": raw_values[2],
        "db_password": raw_values[3],
        "service_token": raw_values[4],
        "client_secret": raw_values[5],
        "api_key": raw_values[6],
        "credential_file": raw_values[7],
    }
    params_arg = json.dumps(params)
    params_args = (
        [f"--params={params_arg}"]
        if inline_value
        else ["--params", params_arg]
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(VASP_SCRIPT),
            "--poscar",
            str(FIXTURE_DIR / "POSCAR_Si"),
            "--job-type",
            "scf",
            "--output-dir",
            str(tmp_path / "vasp_input"),
            "--kppa",
            "100",
            *params_args,
            "--project-root",
            str(tmp_path),
            "--record-helper-run",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    for raw_value in raw_values:
        assert raw_value not in completed.stdout
    recorded_json = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (tmp_path / ".simflow").rglob("*.json")
    )
    for raw_value in raw_values:
        assert raw_value not in recorded_json
    assert "ENCUT" in recorded_json
    assert "520" in recorded_json
    assert recorded_json.count("<redacted>") >= len(raw_values)


def test_vasp_generator_help_marks_potcar_generation_flags_as_compatibility_only():
    completed = subprocess.run(
        [sys.executable, str(VASP_SCRIPT), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "compatibility-only" in completed.stdout.lower()
    assert "--potcar-root" in completed.stdout
    assert "--use-vaspkit" in completed.stdout


# ── NBANDS policy tests ───────────────────────────────────────

def test_scf_no_nbands():
    """SCF INCAR should not contain NBANDS (ordinary calc, no POTCAR)."""
    mod = _load_module("vasp_gen", VASP_SCRIPT)
    with tempfile.TemporaryDirectory() as tmpdir:
        result = mod.generate_vasp_inputs(
            str(FIXTURE_DIR / "POSCAR_Si"), "scf", tmpdir, kppa=100
        )
        assert result["status"] == "success"
        incar_content = Path(os.path.join(tmpdir, "INCAR")).read_text()
        assert "NBANDS" not in incar_content


def test_bands_no_nbands():
    """Bands INCAR should not contain NBANDS (ordinary calc)."""
    mod = _load_module("vasp_gen", VASP_SCRIPT)
    with tempfile.TemporaryDirectory() as tmpdir:
        result = mod.generate_vasp_inputs(
            str(FIXTURE_DIR / "POSCAR_Si"), "bands", tmpdir, kppa=100
        )
        assert result["status"] == "success"
        incar_content = Path(os.path.join(tmpdir, "INCAR")).read_text()
        assert "NBANDS" not in incar_content


def test_optics_has_nbands_with_nelect():
    """Optics INCAR should contain NBANDS when NELECT is provided."""
    mod = _load_module("vasp_gen", VASP_SCRIPT)
    with tempfile.TemporaryDirectory() as tmpdir:
        # Si 2-atom: ZVAL=4 -> NELECT=8, nions=2
        result = mod.generate_vasp_inputs(
            str(FIXTURE_DIR / "POSCAR_Si"), "optics", tmpdir,
            params={"NELECT": 8}, kppa=100,
        )
        assert result["status"] == "success"
        incar_content = Path(os.path.join(tmpdir, "INCAR")).read_text()
        assert "NBANDS" in incar_content
        # Should be > occupied_bands (ceil(8/2)=4)
        for line in incar_content.split("\n"):
            if "NBANDS" in line and "=" in line:
                nbands_val = int(line.split("=")[1].strip())
                assert nbands_val > 4


def test_user_nbands_preserved():
    """User-explicit NBANDS=20 should be preserved when valid."""
    mod = _load_module("vasp_gen", VASP_SCRIPT)
    with tempfile.TemporaryDirectory() as tmpdir:
        result = mod.generate_vasp_inputs(
            str(FIXTURE_DIR / "POSCAR_Si"), "scf", tmpdir,
            params={"NELECT": 8, "NBANDS": 20}, kppa=100,
        )
        assert result["status"] == "success"
        incar_content = Path(os.path.join(tmpdir, "INCAR")).read_text()
        assert "NBANDS" in incar_content
        assert "20" in incar_content


def test_user_nbands_too_small_raises():
    """User-explicit NBANDS=4 with NELECT=8 (occupied=4) should raise."""
    mod = _load_module("vasp_gen", VASP_SCRIPT)
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            mod.generate_vasp_inputs(
                str(FIXTURE_DIR / "POSCAR_Si"), "scf", tmpdir,
                params={"NELECT": 8, "NBANDS": 4}, kppa=100,
            )
            assert False, "Should have raised ValueError"
        except (ValueError, SystemExit):
            pass  # Expected


def test_residual_nbands_removed_in_scf():
    """Residual NBANDS in params should be removed for ordinary SCF."""
    mod = _load_module("vasp_gen", VASP_SCRIPT)
    with tempfile.TemporaryDirectory() as tmpdir:
        # Pass NBANDS="auto" (sentinel -> treated as not specified)
        result = mod.generate_vasp_inputs(
            str(FIXTURE_DIR / "POSCAR_Si"), "scf", tmpdir,
            params={"NELECT": 8, "NBANDS": "auto"}, kppa=100,
        )
        assert result["status"] == "success"
        incar_content = Path(os.path.join(tmpdir, "INCAR")).read_text()
        # "auto" sentinel -> policy removes NBANDS
        assert "NBANDS" not in incar_content


# ── NCORE / NPAR policy tests ─────────────────────────────────

def test_vasp_generator_unknown_context_omits_ncore_npar():
    mod = _load_module("vasp_gen_ncore_unknown", VASP_SCRIPT)
    with tempfile.TemporaryDirectory() as tmpdir:
        result = mod.generate_vasp_inputs(
            str(FIXTURE_DIR / "POSCAR_Si"), "scf", tmpdir, kppa=100
        )
        assert result["status"] == "success"
        incar_content = Path(os.path.join(tmpdir, "INCAR")).read_text()
        assert "NCORE" not in incar_content
        assert "NPAR" not in incar_content
        assert result["incar_policy"]["ncore_npar"]["status"] == "needs_inputs"


def test_vasp_generator_cpu_context_defaults_to_npar():
    mod = _load_module("vasp_gen_ncore_cpu", VASP_SCRIPT)
    with tempfile.TemporaryDirectory() as tmpdir:
        result = mod.generate_vasp_inputs(
            str(FIXTURE_DIR / "POSCAR_Si"), "scf", tmpdir,
            params={"execution_mode": "cpu"}, kppa=100,
        )
        assert result["status"] == "success"
        incar_content = Path(os.path.join(tmpdir, "INCAR")).read_text()
        assert "NPAR" in incar_content
        assert "4" in incar_content
        assert "execution_mode" not in incar_content


def test_vasp_generator_accelerated_context_omits_ncore_npar():
    mod = _load_module("vasp_gen_ncore_gpu", VASP_SCRIPT)
    with tempfile.TemporaryDirectory() as tmpdir:
        result = mod.generate_vasp_inputs(
            str(FIXTURE_DIR / "POSCAR_Si"), "scf", tmpdir,
            params={"execution_mode": "openacc"}, kppa=100,
        )
        assert result["status"] == "success"
        incar_content = Path(os.path.join(tmpdir, "INCAR")).read_text()
        assert "NCORE" not in incar_content
        assert "NPAR" not in incar_content
        assert result["incar_policy"]["ncore_npar"]["execution_context"] == "accelerated"


def test_template_generator_unknown_context_omits_unresolved_blocks_and_ncore():
    mod = _load_module("input_gen_ncore_unknown", INPUT_GEN_SCRIPT)
    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, "INCAR")
        mod.generate_incar("scf", {"job_name": "test"}, out)
        content = Path(out).read_text()
        assert "{%" not in content
        assert "NCORE" not in content
        assert "NPAR" not in content


def test_template_generator_cpu_context_writes_npar_not_ncore():
    mod = _load_module("input_gen_ncore_cpu", INPUT_GEN_SCRIPT)
    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, "INCAR")
        mod.generate_incar("scf", {"job_name": "test", "execution_mode": "cpu"}, out)
        content = Path(out).read_text()
        assert "NPAR" in content
        assert "4" in content
        assert "NCORE" not in content


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        print(f"  {t.__name__}...", end=" ")
        t()
        print("OK")
    print(f"\n  All {len(tests)} tests passed!")
