"""Tests for the skill script contract audit utility."""

from __future__ import annotations

import re
from pathlib import Path

from scripts.audit_skill_scripts import audit_skill_scripts


ROOT = Path(__file__).resolve().parents[2]


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def test_audit_skill_scripts_reports_all_skill_scripts():
    reports = audit_skill_scripts(ROOT)
    script_files = sorted(ROOT.glob("skills/*/scripts/*.py"))

    assert len(reports) == len(script_files)
    assert {report["path"] for report in reports} == {
        str(path.relative_to(ROOT)) for path in script_files
    }


def test_audit_identifies_canonical_stage_runner_contracts():
    reports = {report["path"]: report for report in audit_skill_scripts(ROOT)}
    expected = [
        "skills/simflow-modeling/scripts/run_modeling_stage.py",
        "skills/simflow-computation/scripts/run_input_generation_stage.py",
        "skills/simflow-computation/scripts/run_compute_stage.py",
        "skills/simflow-analysis-visualization/scripts/run_analysis_stage.py",
        "skills/simflow-analysis-visualization/scripts/run_visualization_stage.py",
        "skills/simflow-writing/scripts/run_writing_stage.py",
    ]

    for path in expected:
        assert reports[path]["category"] == "stage_runner"
        assert reports[path]["stage_runner_contract"] is True


def test_audit_output_contains_contract_fields_for_helper_scripts():
    helper = next(
        report
        for report in audit_skill_scripts(ROOT)
        if report["path"] == "skills/simflow-modeling/scripts/build_structure.py"
    )

    assert helper["category"] == "helper_cli"
    assert "has_project_root_option" in helper
    assert "has_record_helper_run_option" in helper


def test_audit_classifies_checkpoint_wrapper_as_state_admin_not_helper_evidence():
    reports = {report["path"]: report for report in audit_skill_scripts(ROOT)}
    checkpoint = reports["skills/simflow-checkpoint/scripts/manage_checkpoint.py"]

    assert checkpoint["category"] == "state_admin"
    assert checkpoint["has_main"] is True
    assert checkpoint["uses_record_helper_run"] is False
    assert checkpoint["uses_standard_recording_args"] is False


def test_all_helper_cli_scripts_support_strict_recording_contract():
    reports = audit_skill_scripts(ROOT)

    failures = []
    for report in reports:
        if report["category"] != "helper_cli":
            continue
        if not report["has_project_root_option"]:
            failures.append(f"{report['path']}: missing --project-root")
        if not report["has_stage_option"]:
            failures.append(f"{report['path']}: missing --stage")
        if not report["has_record_helper_run_option"]:
            failures.append(f"{report['path']}: missing --record-helper-run")
        if not report["uses_record_helper_run"]:
            failures.append(f"{report['path']}: does not call helper-run recording")

    assert failures == []


def test_no_skill_script_uses_omx_as_workflow_state():
    reports = audit_skill_scripts(ROOT)

    assert [report["path"] for report in reports if report["mentions_omx"]] == []


def test_docs_define_helper_recording_as_record_only_and_stage_runner_owned():
    paths = [
        ROOT / "skills" / "simflow-vasp" / "SKILL.md",
        ROOT / "skills" / "simflow-cp2k" / "SKILL.md",
        ROOT / "skills" / "simflow-gpumd" / "SKILL.md",
        ROOT / "skills" / "simflow-mlp" / "SKILL.md",
        ROOT / "skills" / "simflow-mlp" / "references" / "mlp_artifact_schemas.md",
        ROOT / "docs" / "skill-design.md",
        ROOT / "docs" / "software-skills.md",
        ROOT / "docs" / "state-and-checkpoint.md",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in paths).lower()

    for phrase in [
        "--record-helper-run",
        "record_only",
        "simflow.result.v1",
        "top-level statuses are compatibility fields",
        "stage runners own stage transitions",
        "checkpoint",
        "checkpoint operations",
        "helper outputs",
        "do not initialize",
        "do not advance stages",
        "do not create checkpoints",
        "reports/<engine>/",
        "direct helpers do not register arbitrary report artifacts",
        "stage runners may ingest/register outputs",
    ]:
        assert phrase in combined


def test_docs_reject_stale_helper_orchestrator_claims_and_vasp_potcar_generation():
    vasp = (ROOT / "skills" / "simflow-vasp" / "SKILL.md").read_text(encoding="utf-8").lower()
    cp2k = (ROOT / "skills" / "simflow-cp2k" / "SKILL.md").read_text(encoding="utf-8").lower()
    gpumd = (ROOT / "skills" / "simflow-gpumd" / "SKILL.md").read_text(encoding="utf-8").lower()
    software = " ".join(
        (ROOT / "docs" / "software-skills.md")
        .read_text(encoding="utf-8")
        .lower()
        .split()
    )
    skill_design = (ROOT / "docs" / "skill-design.md").read_text(encoding="utf-8").lower()

    assert "do not generate, concatenate, copy, move, print, snapshot, or invoke vaspkit" in _normalize_whitespace(vasp)
    assert "`scripts/orchestrate_vasp_task.py`: build simflow vasp reports, artifacts, and checkpoint records" not in _normalize_whitespace(vasp)
    assert "`scripts/orchestrate_cp2k_task.py`: build simflow cp2k reports, artifacts, checkpoints" not in _normalize_whitespace(cp2k)
    assert "`scripts/orchestrate_gpumd_task.py`: build simflow reports, artifacts, checkpoints" not in _normalize_whitespace(gpumd)
    assert "do not initialize/advance stages, register artifacts, or create checkpoints unless explicit helper-run recording is requested" in software
    assert "writes reports or helper-run metadata under `.simflow/` only when given a project root" not in software
    assert "artifact registration suggestions" not in software
    assert "with `--record-helper-run`, they must use" in skill_design
