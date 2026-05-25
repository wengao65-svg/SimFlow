"""Tests for the skill script contract audit utility."""

from __future__ import annotations

from pathlib import Path

from scripts.audit_skill_scripts import audit_skill_scripts


ROOT = Path(__file__).resolve().parents[2]


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
