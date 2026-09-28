"""Meaningful behavior and write-boundary tests for standalone GPUMD/NEP helpers."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills" / "simflow-gpumd" / "scripts"


def run(script: str, *args: str, success: bool = True) -> dict:
    completed = subprocess.run(
        [sys.executable, str(SCRIPTS / script), *map(str, args)],
        cwd=ROOT, text=True, capture_output=True,
    )
    assert (completed.returncode == 0) is success, completed.stderr + completed.stdout
    return json.loads(completed.stdout)


def test_inspection_is_read_only_and_reports_missing_reference(tmp_path):
    (tmp_path / "run.in").write_text("potential nep.txt\nrun 10\n")
    result = run("inspect_gpumd_inputs.py", "--calculation-dir", tmp_path)
    assert result["status"] == "warning"
    assert result["mode"] == "gpumd"
    assert any(item["code"] == "missing_referenced_file" for item in result["warnings"])
    assert sorted(item.name for item in tmp_path.iterdir()) == ["run.in"]


def test_generate_validate_gpumd_and_refuse_overwrite(tmp_path):
    structure = ROOT / "tests/fixtures/Si.cif"
    (tmp_path / "nep.txt").write_text("fixture potential\n")
    calc = tmp_path / "calc"
    args = ("--structure", structure, "--task", "nvt", "--output-dir", calc,
            "--params", '{"potential_file":"nep.txt","steps":10}')
    generated = run("generate_gpumd_inputs.py", *args)
    assert generated["status"] == "success"
    assert (calc / "run.in").is_file()
    validated = run("validate_gpumd_inputs.py", "--task", "nvt", "--calc-dir", calc)
    assert validated["status"] == "pass"
    assert "scientific_readiness" not in validated
    before = (calc / "run.in").read_bytes()
    refusal = run("generate_gpumd_inputs.py", *args, success=False)
    assert "overwrite" in refusal["message"]
    assert (calc / "run.in").read_bytes() == before
    run("generate_gpumd_inputs.py", *args, "--overwrite")


def test_generate_nep_from_dataset_and_unknown_task_fails(tmp_path):
    (tmp_path / "dataset.xyz").write_text(
        '1\nlattice="5 0 0 0 5 0 0 0 5" energy=-1 properties=species:S:1:pos:R:3:force:R:3\nSi 0 0 0 0 0 0\n'
    )
    calc = tmp_path / "nep_calc"
    result = run("generate_gpumd_inputs.py", "--task", "nep_training", "--software", "nep",
                 "--output-dir", calc, "--params", '{"train_xyz":"dataset.xyz","generation":100}')
    assert result["status"] == "success"
    assert "type 1 Si" in (calc / "nep.in").read_text()
    assert (calc / "train.xyz").read_bytes() == (tmp_path / "dataset.xyz").read_bytes()
    assert run("validate_gpumd_inputs.py", "--task", "nep_training", "--calc-dir", calc)["status"] == "pass"
    invalid = run("generate_gpumd_inputs.py", "--task", "invented", "--output-dir", tmp_path / "bad", success=False)
    assert "Unknown GPUMD/NEP task" in invalid["message"]


def test_gpumd_generator_rejects_multiline_parameter_before_writing(tmp_path):
    result = run("generate_gpumd_inputs.py", "--task", "nvt", "--output-dir", tmp_path / "calc",
                 "--params", '{"potential_file":"nep.txt\\nrun 999"}', success=False)
    assert "newlines" in result["message"]
    assert not (tmp_path / "calc").exists()


def test_parser_distinguishes_numeric_partial_and_missing_without_writes(tmp_path):
    table = tmp_path / "thermo.out"
    table.write_text("1 300\n2 310\ninvalid line\n")
    parsed = run("parse_gpumd_outputs.py", "--files", table)
    assert parsed["parser_status"] == "partial"
    assert parsed["files"][0]["rows"] == 2
    assert parsed["files"][0]["column_ranges"][1]["final"] == 310
    missing = run("parse_gpumd_outputs.py", "--files", tmp_path / "missing.out")
    assert missing["status"] == "blocked"
    assert sorted(item.name for item in tmp_path.iterdir()) == ["thermo.out"]


def test_reports_are_opt_in_and_handoff_preserves_degradation(tmp_path):
    source = tmp_path / "run.in"
    source.write_text("potential missing.txt\n")
    manifest = run("build_gpumd_manifest.py", "--files", source)
    assert manifest["status"] == "success"
    assert sorted(item.name for item in tmp_path.iterdir()) == ["run.in"]
    report = tmp_path / "manifest.json"
    run("build_gpumd_manifest.py", "--files", source, tmp_path / "absent", "--report", report)
    handoff = run("prepare_gpumd_handoff.py", "--manifest", report)
    assert handoff["status"] == "warning"
    assert handoff["sources"][0]["source_status"] == "warning"
    assert not (tmp_path / "handoff.json").exists()
