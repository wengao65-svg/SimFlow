#!/usr/bin/env python3
"""Tests for simflow-handoff canonical registry behavior."""

import json
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "skills" / "simflow-handoff" / "scripts"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(ROOT))

from runtime.lib.state import init_workflow, read_state, write_state
from generate_handoff import generate_handoff
from generate_final_handoff import generate_final_handoff


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


def _write_backbone_state(tmpdir: str):
    workflow = read_state(tmpdir, "workflow.json")
    workflow.update({
        "current_stage": "proposal",
        "status": "in_progress",
        "plan": "plans/workflow_plan.json",
        "stages": ["legacy_stage"],
        "stage_states": {"legacy_stage": "completed"},
    })
    write_state(workflow, project_root=tmpdir, state_file="workflow.json")
    write_state(
        {
            "workflow_id": workflow["workflow_id"],
            "workflow_type": "dft",
            "entry_point": "literature",
            "current_stage": "proposal",
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
            "literature": {
                "stage_name": "literature",
                "status": "completed",
                "agent": None,
                "inputs": [],
                "outputs": [],
                "checkpoint_id": None,
                "error_message": None,
                "started_at": None,
                "completed_at": "2026-01-01T00:00:00+00:00",
            },
            "review": {
                "stage_name": "review",
                "status": "completed",
                "agent": None,
                "inputs": [],
                "outputs": [],
                "checkpoint_id": None,
                "error_message": None,
                "started_at": None,
                "completed_at": "2026-01-02T00:00:00+00:00",
            },
            "proposal": {
                "stage_name": "proposal",
                "status": "in_progress",
                "agent": None,
                "inputs": [],
                "outputs": [],
                "checkpoint_id": None,
                "error_message": None,
                "started_at": "2026-01-03T00:00:00+00:00",
                "completed_at": None,
            },
        },
        project_root=tmpdir,
        state_file="stages.json",
    )
    write_state(
        [
            {
                "artifact_id": "art_lit01",
                "name": "literature_matrix.json",
                "type": "literature_matrix",
                "version": "v1.0.0",
                "stage": "literature",
                "path": ".simflow/artifacts/literature/literature_matrix.json",
                "created_at": "2026-01-01T00:00:00+00:00",
            },
            {
                "artifact_id": "art_lit02",
                "name": "literature_matrix.csv",
                "type": "literature_matrix_csv",
                "version": "v1.0.0",
                "stage": "literature",
                "path": ".simflow/artifacts/literature/literature_matrix.csv",
                "created_at": "2026-01-01T00:05:00+00:00",
            },
            {
                "artifact_id": "art_review01",
                "name": "review_summary.md",
                "type": "review_summary",
                "version": "v1.0.0",
                "stage": "review",
                "path": ".simflow/reports/review/review_summary.md",
                "created_at": "2026-01-02T00:00:00+00:00",
            },
            {
                "artifact_id": "art_review02",
                "name": "gap_analysis.md",
                "type": "gap_analysis",
                "version": "v1.0.0",
                "stage": "review",
                "path": ".simflow/reports/review/gap_analysis.md",
                "created_at": "2026-01-02T00:05:00+00:00",
            },
            {
                "artifact_id": "art_prop01",
                "name": "proposal.md",
                "type": "proposal",
                "version": "v1.0.0",
                "stage": "proposal",
                "path": ".simflow/plans/proposal.md",
                "created_at": "2026-01-03T00:00:00+00:00",
            },
            {
                "artifact_id": "art_prop02",
                "name": "parameter_table.csv",
                "type": "parameter_table",
                "version": "v1.0.0",
                "stage": "proposal",
                "path": ".simflow/plans/parameter_table.csv",
                "created_at": "2026-01-03T00:05:00+00:00",
            },
            {
                "artifact_id": "art_prop03",
                "name": "research_questions.json",
                "type": "research_questions",
                "version": "v1.0.0",
                "stage": "proposal",
                "path": ".simflow/plans/research_questions.json",
                "created_at": "2026-01-03T00:10:00+00:00",
            },
        ],
        project_root=tmpdir,
        state_file="artifacts.json",
    )
    write_state(
        [
            {
                "checkpoint_id": "ckpt_001_literature",
                "workflow_id": workflow["workflow_id"],
                "stage_id": "literature",
                "status": "success",
                "path": ".simflow/checkpoints/ckpt_001_literature.json",
                "created_at": "2026-01-01T00:00:00+00:00",
            },
            {
                "checkpoint_id": "ckpt_002_review",
                "workflow_id": workflow["workflow_id"],
                "stage_id": "review",
                "status": "success",
                "path": ".simflow/checkpoints/ckpt_002_review.json",
                "created_at": "2026-01-02T00:00:00+00:00",
            },
        ],
        project_root=tmpdir,
        state_file="checkpoints.json",
    )
    legacy_root = Path(tmpdir) / ".simflow"
    (legacy_root / "metadata.json").write_text(json.dumps({"workflow_type": "legacy"}, indent=2), encoding="utf-8")
    (legacy_root / "artifacts").mkdir(parents=True, exist_ok=True)
    (legacy_root / "artifacts" / "legacy.json").write_text(
        json.dumps({"artifact_id": "legacy_art", "stage": "legacy_stage"}, indent=2),
        encoding="utf-8",
    )


def _write_milestone_d_state(tmpdir: str):
    project_root = Path(tmpdir)
    workflow = read_state(tmpdir, "workflow.json")
    workflow_plan_path = project_root / ".simflow" / "plans" / "workflow_plan.json"
    latest_checkpoint_path = project_root / ".simflow" / "checkpoints" / "ckpt_009_writing.json"
    workflow.update({
        "current_stage": "writing",
        "status": "completed",
        "plan": str(workflow_plan_path),
    })
    write_state(workflow, project_root=tmpdir, state_file="workflow.json")
    workflow_plan_path.parent.mkdir(parents=True, exist_ok=True)
    workflow_plan_path.write_text(json.dumps({"goal": "Study Si surface reconstruction"}, indent=2), encoding="utf-8")

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

    proposal_path = project_root / ".simflow" / "plans" / "proposal.md"
    parameter_table_path = project_root / ".simflow" / "plans" / "parameter_table.csv"
    research_questions_path = project_root / ".simflow" / "plans" / "research_questions.json"
    structure_manifest_path = project_root / ".simflow" / "reports" / "modeling" / "structure_manifest.json"
    compute_plan_path = project_root / ".simflow" / "reports" / "compute" / "compute_plan.json"
    analysis_report_path = project_root / ".simflow" / "reports" / "analysis" / "analysis_report.json"
    figures_manifest_path = project_root / ".simflow" / "reports" / "visualization" / "figures_manifest.json"
    methods_path = project_root / ".simflow" / "reports" / "writing" / "methods.md"
    results_path = project_root / ".simflow" / "reports" / "writing" / "results.md"
    reproducibility_package_path = project_root / ".simflow" / "reports" / "reproducibility" / "reproducibility_package.md"
    reproducibility_manifest_path = project_root / ".simflow" / "reports" / "reproducibility" / "reproducibility_manifest.json"

    proposal_path.parent.mkdir(parents=True, exist_ok=True)
    parameter_table_path.parent.mkdir(parents=True, exist_ok=True)
    research_questions_path.parent.mkdir(parents=True, exist_ok=True)
    structure_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    compute_plan_path.parent.mkdir(parents=True, exist_ok=True)
    analysis_report_path.parent.mkdir(parents=True, exist_ok=True)
    figures_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    methods_path.parent.mkdir(parents=True, exist_ok=True)
    results_path.parent.mkdir(parents=True, exist_ok=True)
    reproducibility_package_path.parent.mkdir(parents=True, exist_ok=True)

    proposal_path.write_text("# Proposal\n", encoding="utf-8")
    parameter_table_path.write_text("parameter,value\nencut,520\n", encoding="utf-8")
    research_questions_path.write_text(json.dumps({"questions": ["What drives surface reconstruction?"]}, indent=2), encoding="utf-8")
    structure_manifest_path.write_text(json.dumps({"source_mode": "prototype", "structure_files": ["structures/si001.cif"], "validation": {"status": "ok"}}, indent=2), encoding="utf-8")
    compute_plan_path.write_text(json.dumps({"dry_run": True, "real_submit": False, "approval_required_for_real_submit": True}, indent=2), encoding="utf-8")
    analysis_report_path.write_text(json.dumps({"status": "waiting_for_outputs", "software": "vasp", "task": "relax", "conclusions": "Awaiting outputs."}, indent=2), encoding="utf-8")
    figures_manifest_path.write_text(json.dumps({"status": "waiting_for_outputs", "figures": [{"name": "energy_convergence.png", "path": ".simflow/artifacts/visualization/energy_convergence.png", "title": "Energy Convergence"}], "skipped_reasons": []}, indent=2), encoding="utf-8")
    methods_path.write_text("# Methods\n", encoding="utf-8")
    results_path.write_text("# Results\n", encoding="utf-8")
    reproducibility_package_path.write_text("# Reproducibility Package\n", encoding="utf-8")
    reproducibility_manifest_path.write_text(
        json.dumps(
            {
                "workflow_metadata": {
                    "workflow_id": workflow["workflow_id"],
                    "workflow_type": "dft",
                    "status": "completed",
                    "current_stage": "writing",
                    "entry_point": "literature",
                    "plan_reference": str(workflow_plan_path),
                    "research_goal": "Study Si surface reconstruction",
                    "material": "Si(001)",
                    "software": "vasp",
                },
                "completed_stages": DFT_STAGES,
                "pending_stages": [],
                "failed_stages": [],
                "checkpoint_summary": {
                    "count": 2,
                    "stage_ids": ["compute", "writing"],
                    "latest": {
                        "checkpoint_id": "ckpt_009_writing",
                        "stage_id": "writing",
                        "status": "success",
                        "path": str(latest_checkpoint_path),
                    },
                },
                "execution_truth": {
                    "dry_run": True,
                    "real_submit": False,
                    "approval_required_for_real_submit": True,
                },
                "figure_provenance": {
                    "status": "waiting_for_outputs",
                    "figure_count": 1,
                    "figures": [
                        {
                            "name": "energy_convergence.png",
                            "path": ".simflow/artifacts/visualization/energy_convergence.png",
                            "artifact_id": "art_fig01",
                        }
                    ],
                    "skipped_reasons": [],
                },
                "writing_artifact_references": {
                    "methods": {"artifact_id": "art_methods01", "name": "methods.md", "type": "methods", "stage": "writing", "path": ".simflow/reports/writing/methods.md", "version": "v1.0.0"},
                    "results": {"artifact_id": "art_results01", "name": "results.md", "type": "results", "stage": "writing", "path": ".simflow/reports/writing/results.md", "version": "v1.0.0"},
                    "reproducibility_package": {"artifact_id": "art_repro_pkg01", "name": "reproducibility_package.md", "type": "reproducibility_package", "stage": "writing", "path": ".simflow/reports/reproducibility/reproducibility_package.md", "version": "v1.0.0"},
                    "reproducibility_manifest": {"artifact_id": "art_repro_manifest01", "name": "reproducibility_manifest.json", "type": "reproducibility_manifest", "stage": "writing", "path": ".simflow/reports/reproducibility/reproducibility_manifest.json", "version": "v1.0.0"},
                },
                "warnings": [
                    {"type": "sanitized_path", "field": "artifact_index[3].lineage.parameters.source_structure", "replacement": "inputs/Si001.cif"}
                ],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    write_state(
        [
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
        ],
        project_root=tmpdir,
        state_file="artifacts.json",
    )
    write_state(
        [
            {"checkpoint_id": "ckpt_008_compute", "workflow_id": workflow["workflow_id"], "stage_id": "compute", "status": "success", "path": ".simflow/checkpoints/ckpt_008_compute.json", "created_at": "2026-01-05T00:00:00+00:00"},
            {"checkpoint_id": "ckpt_009_writing", "workflow_id": workflow["workflow_id"], "stage_id": "writing", "status": "success", "path": str(latest_checkpoint_path), "created_at": "2026-01-08T00:20:00+00:00"},
        ],
        project_root=tmpdir,
        state_file="checkpoints.json",
    )



def test_generate_handoff_uses_canonical_registries():
    with tempfile.TemporaryDirectory() as tmpdir:
        init_workflow("dft", "literature", tmpdir)
        _write_backbone_state(tmpdir)

        result = generate_handoff(str(Path(tmpdir) / ".simflow"))
        handoff = result["handoff"]

        assert result["status"] == "success"
        assert handoff["current_stage"] == "proposal"
        assert handoff["completed_stages"] == ["literature", "review"]
        assert handoff["in_progress_stages"] == ["proposal"]
        assert handoff["pending_stages"] == ["modeling", "input_generation", "compute", "analysis", "visualization", "writing"]
        assert handoff["artifacts_count"] == 7
        assert set(handoff["artifacts_by_stage"].keys()) == {"literature", "review", "proposal"}
        assert [artifact["name"] for artifact in handoff["artifacts_by_stage"]["literature"]] == ["literature_matrix.json", "literature_matrix.csv"]
        assert [artifact["name"] for artifact in handoff["artifacts_by_stage"]["review"]] == ["review_summary.md", "gap_analysis.md"]
        assert [artifact["name"] for artifact in handoff["artifacts_by_stage"]["proposal"]] == ["proposal.md", "parameter_table.csv", "research_questions.json"]
        assert handoff["latest_checkpoint"]["checkpoint_id"] == "ckpt_002_review"
        assert handoff["plan_reference"] == "plans/workflow_plan.json"
        assert handoff["next_steps"] == ["Continue stage: proposal"]
        assert handoff["progress_pct"] == 22.2
        assert "legacy_stage" not in handoff["completed_stages"]
        assert handoff["workflow_type"] == "dft"


def test_generate_handoff_writes_markdown_summary_with_backbone_fields():
    with tempfile.TemporaryDirectory() as tmpdir:
        init_workflow("dft", "literature", tmpdir)
        _write_backbone_state(tmpdir)
        output_path = Path(tmpdir) / ".simflow" / "reports" / "handoff.md"

        result = generate_handoff(str(Path(tmpdir) / ".simflow"), str(output_path))
        content = output_path.read_text(encoding="utf-8")

        assert result["status"] == "success"
        assert result["handoff"]["output_file"] == str(output_path)
        assert "### literature" in content
        assert "### review" in content
        assert "### proposal" in content
        assert "literature_matrix.json" in content
        assert "proposal.md" in content
        assert "Current stage: proposal" in content
        assert "Artifact count: 7" in content
        assert "Plan reference: plans/workflow_plan.json" in content
        assert "Continue stage: proposal" in content
        assert "ckpt_002_review" in content


def test_generate_final_handoff_generates_deliverables_without_leaking_absolute_paths():
    with tempfile.TemporaryDirectory() as tmpdir:
        init_workflow("dft", "literature", tmpdir)
        _write_milestone_d_state(tmpdir)

        result = generate_final_handoff(str(Path(tmpdir) / ".simflow"))
        final_handoff = result["final_handoff"]
        final_json_path = Path(tmpdir) / ".simflow" / "reports" / "handoff" / "final_handoff.json"
        final_md_path = Path(tmpdir) / ".simflow" / "reports" / "handoff" / "final_handoff.md"
        final_json_text = final_json_path.read_text(encoding="utf-8")
        final_md_text = final_md_path.read_text(encoding="utf-8")

        assert result["status"] == "success"
        assert final_json_path.is_file()
        assert final_md_path.is_file()
        assert {artifact["name"] for artifact in result["artifacts"]} == {"final_handoff.md", "final_handoff.json"}
        assert final_handoff["workflow_metadata"]["workflow_type"] == "dft"
        assert final_handoff["current_stage"] == "writing"
        assert final_handoff["latest_checkpoint"]["checkpoint_id"] == "ckpt_009_writing"
        assert final_handoff["compute_truth"]["dry_run"] is True
        assert final_handoff["compute_truth"]["real_submit"] is False
        assert final_handoff["compute_truth"]["approval_required_for_real_submit"] is True
        assert final_handoff["writing_outputs"]["methods"]["name"] == "methods.md"
        assert final_handoff["writing_outputs"]["results"]["name"] == "results.md"
        assert final_handoff["reproducibility_outputs"]["reproducibility_package"]["name"] == "reproducibility_package.md"
        assert "No real HPC submit was executed" in "\n".join(final_handoff["risks"])
        assert "## Writing outputs" in final_md_text
        assert "## Reproducibility package" in final_md_text
        assert "## Compute truth / real submit status" in final_md_text
        assert "ckpt_009_writing" in final_md_text
        assert tmpdir not in final_json_text
        assert tmpdir not in final_md_text



def test_generate_handoff_errors_without_workflow_state():
    with tempfile.TemporaryDirectory() as tmpdir:
        result = generate_handoff(str(Path(tmpdir) / ".simflow"))

        assert result["status"] == "error"
        assert result["message"] == "No workflow state found"
