#!/usr/bin/env python3
"""Tests for final delivery verification helpers."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from runtime.lib.state import init_workflow, read_state, write_state
from runtime.lib.verification import REQUIRED_CHECK_NAMES, build_final_delivery_report

DFT_STAGES = [
    "literature",
    "review",
    "proposal",
    "modeling",
    "input_generation",
    "compute",
    "analysis",
    "visualization",
    "writing",
]


def _check_map(report: dict) -> dict:
    return {check["name"]: check for check in report["checks"]}


def _write_final_delivery_state(
    tmpdir: str,
    *,
    include_final_handoff_json: bool = True,
    real_submit: bool = False,
    approval_required: bool = True,
    approval_gate_status: str | None = None,
    include_redacted_secret: bool = False,
) -> None:
    project_root = Path(tmpdir)
    workflow = read_state(tmpdir, "workflow.json")
    workflow.update({
        "current_stage": "writing",
        "status": "completed",
        "plan": "plans/workflow_plan.json",
    })
    write_state(workflow, project_root=tmpdir, state_file="workflow.json")
    write_state(
        {
            "workflow_id": workflow["workflow_id"],
            "workflow_type": "dft",
            "entry_point": "literature",
            "current_stage": "writing",
            "stages": DFT_STAGES,
            "research_goal": "Study Si surface reconstruction",
            "material": "Si(001)",
            "software": "vasp",
        },
        project_root=tmpdir,
        state_file="metadata.json",
    )
    write_state(
        {
            stage: {
                "stage_name": stage,
                "status": "completed",
                "agent": None,
                "inputs": [],
                "outputs": [],
                "checkpoint_id": None,
                "error_message": None,
                "started_at": "2026-01-01T00:00:00+00:00",
                "completed_at": "2026-01-01T00:10:00+00:00",
            }
            for stage in DFT_STAGES
        },
        project_root=tmpdir,
        state_file="stages.json",
    )

    files = {
        "proposal": project_root / ".simflow" / "plans" / "proposal.md",
        "parameter_table": project_root / ".simflow" / "plans" / "parameter_table.csv",
        "research_questions": project_root / ".simflow" / "plans" / "research_questions.json",
        "structure_manifest": project_root / ".simflow" / "reports" / "modeling" / "structure_manifest.json",
        "compute_plan": project_root / ".simflow" / "reports" / "compute" / "compute_plan.json",
        "analysis_report": project_root / ".simflow" / "reports" / "analysis" / "analysis_report.json",
        "figures_manifest": project_root / ".simflow" / "reports" / "visualization" / "figures_manifest.json",
        "methods": project_root / ".simflow" / "reports" / "writing" / "methods.md",
        "results": project_root / ".simflow" / "reports" / "writing" / "results.md",
        "reproducibility_package": project_root / ".simflow" / "reports" / "reproducibility" / "reproducibility_package.md",
        "reproducibility_manifest": project_root / ".simflow" / "reports" / "reproducibility" / "reproducibility_manifest.json",
        "final_handoff_markdown": project_root / ".simflow" / "reports" / "handoff" / "final_handoff.md",
        "final_handoff_json": project_root / ".simflow" / "reports" / "handoff" / "final_handoff.json",
    }
    for path in files.values():
        path.parent.mkdir(parents=True, exist_ok=True)

    files["proposal"].write_text("# Proposal\n", encoding="utf-8")
    files["parameter_table"].write_text("parameter,value\nencut,520\n", encoding="utf-8")
    files["research_questions"].write_text(json.dumps({"questions": ["What drives surface reconstruction?"]}, indent=2), encoding="utf-8")
    files["structure_manifest"].write_text(json.dumps({"source_mode": "prototype", "structure_files": ["structures/si001.cif"], "validation": {"status": "ok"}}, indent=2), encoding="utf-8")
    files["analysis_report"].write_text(json.dumps({"status": "waiting_for_outputs", "software": "vasp", "task": "relax", "conclusions": "Awaiting outputs."}, indent=2), encoding="utf-8")
    files["figures_manifest"].write_text(json.dumps({"status": "waiting_for_outputs", "figures": [], "skipped_reasons": []}, indent=2), encoding="utf-8")
    files["methods"].write_text("# Methods\n", encoding="utf-8")
    files["results"].write_text("# Results\n", encoding="utf-8")
    files["reproducibility_package"].write_text("# Reproducibility Package\n", encoding="utf-8")
    files["final_handoff_markdown"].write_text("# Final Handoff\n", encoding="utf-8")

    execution_truth = {
        "dry_run": True,
        "real_submit": real_submit,
        "approval_required_for_real_submit": approval_required,
    }
    if approval_gate_status is not None:
        execution_truth["approval_gate_status"] = approval_gate_status
    files["compute_plan"].write_text(json.dumps(execution_truth, indent=2), encoding="utf-8")

    reproducibility_manifest = {
        "workflow_metadata": {
            "workflow_id": workflow["workflow_id"],
            "workflow_type": "dft",
            "status": "completed",
            "current_stage": "writing",
            "entry_point": "literature",
            "plan_reference": "plans/workflow_plan.json",
            "research_goal": "Study Si surface reconstruction",
            "material": "Si(001)",
            "software": "vasp",
        },
        "completed_stages": DFT_STAGES,
        "pending_stages": [],
        "failed_stages": [],
        "checkpoint_summary": {
            "count": 1,
            "stage_ids": ["writing"],
            "latest": {
                "checkpoint_id": "ckpt_009_writing",
                "stage_id": "writing",
                "status": "success",
                "path": ".simflow/checkpoints/ckpt_009_writing.json",
            },
        },
        "execution_truth": execution_truth,
        "figure_provenance": {
            "status": "waiting_for_outputs",
            "figure_count": 0,
            "figures": [],
            "skipped_reasons": [],
        },
        "writing_artifact_references": {
            "methods": {"artifact_id": "art_methods01", "name": "methods.md", "type": "methods", "stage": "writing", "path": ".simflow/reports/writing/methods.md", "version": "v1.0.0"},
            "results": {"artifact_id": "art_results01", "name": "results.md", "type": "results", "stage": "writing", "path": ".simflow/reports/writing/results.md", "version": "v1.0.0"},
            "reproducibility_package": {"artifact_id": "art_repro_pkg01", "name": "reproducibility_package.md", "type": "reproducibility_package", "stage": "writing", "path": ".simflow/reports/reproducibility/reproducibility_package.md", "version": "v1.0.0"},
            "reproducibility_manifest": {"artifact_id": "art_repro_manifest01", "name": "reproducibility_manifest.json", "type": "reproducibility_manifest", "stage": "writing", "path": ".simflow/reports/reproducibility/reproducibility_manifest.json", "version": "v1.0.0"},
        },
        "warnings": [],
    }
    if include_redacted_secret:
        reproducibility_manifest["security"] = {"api_token": "<redacted>"}
    files["reproducibility_manifest"].write_text(
        json.dumps(reproducibility_manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    artifact_entries = [
        {"artifact_id": "art_prop01", "name": "proposal.md", "type": "proposal", "version": "v1.0.0", "stage": "proposal", "path": ".simflow/plans/proposal.md", "lineage": {"parent_artifacts": [], "parameters": {}, "software": "vasp"}, "created_at": "2026-01-03T00:00:00+00:00"},
        {"artifact_id": "art_param01", "name": "parameter_table.csv", "type": "parameter_table", "version": "v1.0.0", "stage": "proposal", "path": ".simflow/plans/parameter_table.csv", "lineage": {"parent_artifacts": ["art_prop01"], "parameters": {}, "software": "vasp"}, "created_at": "2026-01-03T00:05:00+00:00"},
        {"artifact_id": "art_questions01", "name": "research_questions.json", "type": "research_questions", "version": "v1.0.0", "stage": "proposal", "path": ".simflow/plans/research_questions.json", "lineage": {"parent_artifacts": ["art_prop01"], "parameters": {}, "software": "vasp"}, "created_at": "2026-01-03T00:10:00+00:00"},
        {"artifact_id": "art_struct01", "name": "structure_manifest.json", "type": "structure_manifest", "version": "v1.0.0", "stage": "modeling", "path": ".simflow/reports/modeling/structure_manifest.json", "lineage": {"parent_artifacts": ["art_prop01", "art_param01", "art_questions01"], "parameters": {}, "software": "vasp"}, "created_at": "2026-01-04T00:00:00+00:00"},
        {"artifact_id": "art_compute01", "name": "compute_plan.json", "type": "compute_plan", "version": "v1.0.0", "stage": "compute", "path": ".simflow/reports/compute/compute_plan.json", "lineage": {"parent_artifacts": ["art_struct01"], "parameters": {}, "software": "vasp"}, "created_at": "2026-01-05T00:00:00+00:00"},
        {"artifact_id": "art_analysis01", "name": "analysis_report.json", "type": "analysis_report", "version": "v1.0.0", "stage": "analysis", "path": ".simflow/reports/analysis/analysis_report.json", "lineage": {"parent_artifacts": ["art_compute01"], "parameters": {}, "software": "vasp"}, "created_at": "2026-01-06T00:00:00+00:00"},
        {"artifact_id": "art_figman01", "name": "figures_manifest.json", "type": "figures_manifest", "version": "v1.0.0", "stage": "visualization", "path": ".simflow/reports/visualization/figures_manifest.json", "lineage": {"parent_artifacts": ["art_analysis01"], "parameters": {}, "software": "vasp"}, "created_at": "2026-01-07T00:00:00+00:00"},
        {"artifact_id": "art_methods01", "name": "methods.md", "type": "methods", "version": "v1.0.0", "stage": "writing", "path": ".simflow/reports/writing/methods.md", "lineage": {"parent_artifacts": ["art_prop01", "art_param01", "art_questions01", "art_struct01", "art_compute01", "art_analysis01", "art_figman01"], "parameters": {}, "software": "vasp"}, "created_at": "2026-01-08T00:00:00+00:00"},
        {"artifact_id": "art_results01", "name": "results.md", "type": "results", "version": "v1.0.0", "stage": "writing", "path": ".simflow/reports/writing/results.md", "lineage": {"parent_artifacts": ["art_methods01", "art_prop01", "art_param01", "art_questions01", "art_struct01", "art_compute01", "art_analysis01", "art_figman01"], "parameters": {}, "software": "vasp"}, "created_at": "2026-01-08T00:05:00+00:00"},
        {"artifact_id": "art_repro_manifest01", "name": "reproducibility_manifest.json", "type": "reproducibility_manifest", "version": "v1.0.0", "stage": "writing", "path": ".simflow/reports/reproducibility/reproducibility_manifest.json", "lineage": {"parent_artifacts": ["art_methods01", "art_results01", "art_prop01", "art_param01", "art_questions01", "art_struct01", "art_compute01", "art_analysis01", "art_figman01"], "parameters": {}, "software": "vasp"}, "created_at": "2026-01-08T00:10:00+00:00"},
        {"artifact_id": "art_repro_pkg01", "name": "reproducibility_package.md", "type": "reproducibility_package", "version": "v1.0.0", "stage": "writing", "path": ".simflow/reports/reproducibility/reproducibility_package.md", "lineage": {"parent_artifacts": ["art_methods01", "art_results01", "art_repro_manifest01", "art_prop01", "art_param01", "art_questions01", "art_struct01", "art_compute01", "art_analysis01", "art_figman01"], "parameters": {}, "software": "vasp"}, "created_at": "2026-01-08T00:15:00+00:00"},
        {"artifact_id": "art_handoff_md01", "name": "final_handoff.md", "type": "final_handoff", "version": "v1.0.0", "stage": "writing", "path": ".simflow/reports/handoff/final_handoff.md", "lineage": {"parent_artifacts": ["art_methods01", "art_results01", "art_repro_pkg01", "art_repro_manifest01", "art_prop01", "art_param01", "art_questions01", "art_struct01", "art_compute01", "art_analysis01", "art_figman01"], "parameters": {}, "software": "vasp"}, "created_at": "2026-01-08T00:20:00+00:00"},
    ]
    if include_final_handoff_json:
        final_handoff = {
            "workflow_metadata": {
                "workflow_id": workflow["workflow_id"],
                "workflow_type": "dft",
                "status": "completed",
                "current_stage": "writing",
                "entry_point": "literature",
                "plan_reference": "plans/workflow_plan.json",
                "research_goal": "Study Si surface reconstruction",
                "material": "Si(001)",
                "software": "vasp",
            },
            "current_stage": "writing",
            "completed_stages": DFT_STAGES,
            "pending_stages": [],
            "failed_stages": [],
            "latest_checkpoint": {
                "checkpoint_id": "ckpt_009_writing",
                "stage_id": "writing",
                "status": "success",
                "path": ".simflow/checkpoints/ckpt_009_writing.json",
            },
            "artifact_summary": {
                "artifacts_count": 11,
                "artifacts_by_stage": {"writing": 5},
                "artifacts_by_type": {"final_handoff": 1},
            },
            "writing_outputs": {
                "methods": {"artifact_id": "art_methods01", "name": "methods.md", "type": "methods", "stage": "writing", "path": ".simflow/reports/writing/methods.md"},
                "results": {"artifact_id": "art_results01", "name": "results.md", "type": "results", "stage": "writing", "path": ".simflow/reports/writing/results.md"},
                "final_handoff_markdown": {"artifact_id": "art_handoff_md01", "name": "final_handoff.md", "type": "final_handoff", "stage": "writing", "path": ".simflow/reports/handoff/final_handoff.md"},
                "final_handoff_json": {"artifact_id": "art_handoff_json01", "name": "final_handoff.json", "type": "final_handoff_summary", "stage": "writing", "path": ".simflow/reports/handoff/final_handoff.json"},
            },
            "reproducibility_outputs": {
                "reproducibility_package": {"artifact_id": "art_repro_pkg01", "name": "reproducibility_package.md", "type": "reproducibility_package", "stage": "writing", "path": ".simflow/reports/reproducibility/reproducibility_package.md"},
                "reproducibility_manifest": {"artifact_id": "art_repro_manifest01", "name": "reproducibility_manifest.json", "type": "reproducibility_manifest", "stage": "writing", "path": ".simflow/reports/reproducibility/reproducibility_manifest.json"},
            },
            "compute_truth": execution_truth,
            "risks": [],
            "unresolved_items": [],
            "next_steps": ["Workflow complete"],
            "source_artifact_ids": ["art_prop01", "art_param01", "art_questions01", "art_struct01", "art_compute01", "art_analysis01", "art_figman01"],
            "generated_at": "2026-01-08T00:25:00+00:00",
        }
        if include_redacted_secret:
            final_handoff["security"] = {"password": "<redacted>"}
        files["final_handoff_json"].write_text(json.dumps(final_handoff, indent=2, ensure_ascii=False), encoding="utf-8")
        artifact_entries.append(
            {"artifact_id": "art_handoff_json01", "name": "final_handoff.json", "type": "final_handoff_summary", "version": "v1.0.0", "stage": "writing", "path": ".simflow/reports/handoff/final_handoff.json", "lineage": {"parent_artifacts": ["art_methods01", "art_results01", "art_repro_pkg01", "art_repro_manifest01", "art_prop01", "art_param01", "art_questions01", "art_struct01", "art_compute01", "art_analysis01", "art_figman01"], "parameters": {}, "software": "vasp"}, "created_at": "2026-01-08T00:18:00+00:00"}
        )

    write_state(artifact_entries, project_root=tmpdir, state_file="artifacts.json")
    write_state(
        [
            {"checkpoint_id": "ckpt_009_writing", "workflow_id": workflow["workflow_id"], "stage_id": "writing", "status": "success", "path": ".simflow/checkpoints/ckpt_009_writing.json", "created_at": "2026-01-08T00:20:00+00:00"},
        ],
        project_root=tmpdir,
        state_file="checkpoints.json",
    )


def test_build_final_delivery_report_passes_with_complete_artifacts():
    with tempfile.TemporaryDirectory() as tmpdir:
        init_workflow("dft", "literature", tmpdir)
        _write_final_delivery_state(tmpdir)

        report = build_final_delivery_report(project_root=tmpdir)
        checks = _check_map(report)

        assert report["status"] == "pass"
        assert set(checks) == set(REQUIRED_CHECK_NAMES)
        assert report["failures"] == []
        assert checks["required_writing_outputs"]["status"] == "pass"
        assert checks["artifact_traceability"]["status"] == "pass"
        assert checks["compute_truth_declared"]["status"] == "pass"
        assert checks["no_real_submit_without_approval"]["status"] == "pass"


def test_build_final_delivery_report_fails_without_final_handoff_json():
    with tempfile.TemporaryDirectory() as tmpdir:
        init_workflow("dft", "literature", tmpdir)
        _write_final_delivery_state(tmpdir, include_final_handoff_json=False)

        report = build_final_delivery_report(project_root=tmpdir)
        checks = _check_map(report)

        assert report["status"] == "fail"
        assert checks["final_handoff_present"]["status"] == "fail"
        assert checks["required_writing_outputs"]["status"] == "fail"


def test_build_final_delivery_report_fails_when_real_submit_lacks_approval():
    with tempfile.TemporaryDirectory() as tmpdir:
        init_workflow("dft", "literature", tmpdir)
        _write_final_delivery_state(tmpdir, real_submit=True, approval_required=False)

        report = build_final_delivery_report(project_root=tmpdir)
        checks = _check_map(report)

        assert report["status"] == "fail"
        assert checks["compute_truth_declared"]["status"] == "pass"
        assert checks["no_real_submit_without_approval"]["status"] == "fail"


def test_build_final_delivery_report_warns_on_redacted_sensitive_content():
    with tempfile.TemporaryDirectory() as tmpdir:
        init_workflow("dft", "literature", tmpdir)
        _write_final_delivery_state(tmpdir, include_redacted_secret=True)

        report = build_final_delivery_report(project_root=tmpdir)
        checks = _check_map(report)

        assert report["status"] == "warning"
        assert checks["no_sensitive_paths"]["status"] == "warning"
        assert report["warnings"]
