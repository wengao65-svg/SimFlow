#!/usr/bin/env python3
"""Tests for simflow-pipeline canonical state behavior."""

import importlib.util
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "skills" / "simflow-pipeline" / "scripts"
INTAKE_DIR = Path(__file__).resolve().parents[2] / "skills" / "simflow-intake" / "scripts"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(INTAKE_DIR))
sys.path.insert(0, str(ROOT))

from runtime.lib.artifact import list_artifacts
from runtime.lib.state import init_workflow, read_state, write_state
from run_pipeline import run_pipeline
from init_research import init_research


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

H2O_CIF = ROOT / "examples" / "h2o" / "H2O.cif"
VASP_RUN_XML = ROOT / "tests" / "fixtures" / "vasprun_Si.xml"
CP2K_FIXTURE_DIR = ROOT / "tests" / "fixtures" / "cp2k"


def _write_metadata(tmpdir: str):
    state = read_state(tmpdir, "workflow.json")
    metadata = {
        "workflow_id": state["workflow_id"],
        "workflow_type": "dft",
        "entry_point": "literature",
        "current_stage": "literature",
        "research_goal": "Study Si surface reconstruction",
        "material": "Si(001)",
        "software": "vasp",
        "parameters": {},
        "stages": DFT_STAGES,
    }
    write_state(metadata, project_root=tmpdir, state_file="metadata.json")


def test_run_pipeline_dry_run_uses_canonical_stage_sequence():
    with tempfile.TemporaryDirectory() as tmpdir:
        init_workflow("dft", "literature", tmpdir)
        _write_metadata(tmpdir)
        workflow = read_state(tmpdir, "workflow.json")
        workflow["stages"] = ["legacy_stage"]
        write_state(workflow, project_root=tmpdir, state_file="workflow.json")

        result = run_pipeline(str(Path(tmpdir) / ".simflow"), target_stage="proposal", dry_run=True)
        stages_state = read_state(tmpdir, "stages.json")

        assert result["status"] == "success"
        assert [item["stage"] for item in result["results"]] == ["literature", "review", "proposal"]
        assert all(item["status"] == "dry_run_complete" for item in result["results"])
        assert stages_state["literature"]["status"] == "pending"
        assert stages_state["review"]["status"] == "pending"
        assert stages_state["proposal"]["status"] == "pending"
        assert "legacy_stage" not in stages_state
        assert not (Path(tmpdir) / ".simflow" / "workflow_state.json").exists()


def test_run_pipeline_execute_updates_stages_and_checkpoint_registry():
    with tempfile.TemporaryDirectory() as tmpdir:
        init_workflow("dft", "literature", tmpdir)
        _write_metadata(tmpdir)

        result = run_pipeline(str(Path(tmpdir) / ".simflow"), target_stage="review", dry_run=False)
        workflow = read_state(tmpdir, "workflow.json")
        stages_state = read_state(tmpdir, "stages.json")
        checkpoints = read_state(tmpdir, "checkpoints.json")

        assert result["status"] == "success"
        assert [item["stage"] for item in result["results"]] == ["literature", "review"]
        assert all(item["status"] == "completed" for item in result["results"])
        assert workflow["current_stage"] == "review"
        assert workflow["status"] == "in_progress"
        assert stages_state["literature"]["status"] == "completed"
        assert stages_state["review"]["status"] == "completed"
        assert stages_state["review"]["checkpoint_id"] == result["checkpoint_id"]
        assert len(checkpoints) == 1
        assert checkpoints[0]["checkpoint_id"] == result["checkpoint_id"]
        assert checkpoints[0]["stage_id"] == "review"
        assert not (Path(tmpdir) / ".simflow" / "workflow_state.json").exists()
        assert not (Path(tmpdir) / ".simflow" / "metadata.json").exists()


def test_run_pipeline_execute_starts_after_completed_current_stage():
    with tempfile.TemporaryDirectory() as tmpdir:
        init_workflow("dft", "literature", tmpdir)
        _write_metadata(tmpdir)
        workflow = read_state(tmpdir, "workflow.json")
        workflow["current_stage"] = "modeling"
        write_state(workflow, project_root=tmpdir, state_file="workflow.json")
        write_state(
            {
                "modeling": {
                    "stage_name": "modeling",
                    "status": "completed",
                    "agent": None,
                    "inputs": [],
                    "outputs": [],
                    "checkpoint_id": None,
                    "error_message": None,
                    "started_at": None,
                    "completed_at": "2026-01-01T00:00:00+00:00",
                }
            },
            project_root=tmpdir,
            state_file="stages.json",
        )

        result = run_pipeline(str(Path(tmpdir) / ".simflow"), target_stage="analysis", dry_run=True)

        assert [item["stage"] for item in result["results"]] == ["input_generation", "compute", "analysis"]
        assert all(item["status"] == "dry_run_complete" for item in result["results"])



def test_run_pipeline_execute_runs_research_generators_through_review():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        pdf_path = project_root / "papers" / "surface.pdf"
        bib_path = project_root / "refs" / "references.bib"
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        bib_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_path.write_text("pdf placeholder", encoding="utf-8")
        bib_path.write_text("@article{surface, title={Surface Study}}", encoding="utf-8")

        init_research(
            input_text="\n".join([
                "goal: study Si surface reconstruction",
                "material: Si(001)",
                "parameters: {\"encut\": 520}",
                "pdfs: papers/surface.pdf",
                "bibtex: refs/references.bib",
                "dois: 10.1000/alpha",
                "note: Focus on dimer buckling evidence",
            ]),
            output_dir=tmpdir,
        )

        result = run_pipeline(str(project_root / ".simflow"), target_stage="review", dry_run=False)
        workflow = read_state(tmpdir, "workflow.json")
        stages_state = read_state(tmpdir, "stages.json")
        literature_artifacts = list_artifacts(stage="literature", project_root=tmpdir)
        review_artifacts = list_artifacts(stage="review", project_root=tmpdir)

        assert result["status"] == "success"
        assert [item["stage"] for item in result["results"]] == ["literature", "review"]
        assert result["results"][0]["artifacts"][0]["name"] == "literature_matrix.json"
        assert result["results"][1]["artifacts"][0]["name"] == "review_summary.md"
        assert workflow["current_stage"] == "review"
        assert stages_state["literature"]["status"] == "completed"
        assert stages_state["review"]["status"] == "completed"
        assert len(literature_artifacts) == 2
        assert len(review_artifacts) == 2
        assert stages_state["review"]["inputs"] == [literature_artifacts[0]["artifact_id"]]
        assert (project_root / ".simflow" / "reports" / "review" / "review_summary.md").is_file()


def test_run_pipeline_execute_runs_modeling_stage_through_canonical_runner():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        pdf_path = project_root / "papers" / "surface.pdf"
        bib_path = project_root / "refs" / "references.bib"
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        bib_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_path.write_text("pdf placeholder", encoding="utf-8")
        bib_path.write_text("@article{surface, title={Surface Study}}", encoding="utf-8")

        init_research(
            input_text="\n".join([
                "goal: study Si surface reconstruction",
                "material: Si(001)",
                "software: vasp",
                "parameters: {\"encut\": 520, \"structure_type\": \"diamond\", \"lattice_param\": 5.43, \"elements\": [\"Si\"]}",
                "pdfs: papers/surface.pdf",
                "bibtex: refs/references.bib",
                "dois: 10.1000/alpha",
            ]),
            output_dir=tmpdir,
        )

        result = run_pipeline(str(project_root / ".simflow"), target_stage="modeling", dry_run=False)
        workflow = read_state(tmpdir, "workflow.json")
        stages_state = read_state(tmpdir, "stages.json")
        proposal_artifacts = list_artifacts(stage="proposal", project_root=tmpdir)
        modeling_artifacts = list_artifacts(stage="modeling", project_root=tmpdir)

        assert result["status"] == "success"
        assert [item["stage"] for item in result["results"]] == ["literature", "review", "proposal", "modeling"]
        assert result["results"][-1]["artifacts"][0]["name"] == "structure_manifest.json"
        assert workflow["current_stage"] == "modeling"
        assert workflow["status"] == "in_progress"
        assert stages_state["modeling"]["status"] == "completed"
        assert stages_state["modeling"]["inputs"] == [artifact["artifact_id"] for artifact in proposal_artifacts]
        assert len(stages_state["modeling"]["outputs"]) == 2
        assert {artifact["name"] for artifact in modeling_artifacts} == {"structure_manifest.json", "POSCAR"}
        assert (project_root / ".simflow" / "reports" / "modeling" / "structure_manifest.json").is_file()
        assert (project_root / ".simflow" / "artifacts" / "modeling" / "POSCAR").is_file()


def test_run_pipeline_execute_runs_precompute_vasp_chain():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        pdf_path = project_root / "papers" / "surface.pdf"
        bib_path = project_root / "refs" / "references.bib"
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        bib_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_path.write_text("pdf placeholder", encoding="utf-8")
        bib_path.write_text("@article{surface, title={Surface Study}}", encoding="utf-8")

        init_research(
            input_text="\n".join([
                "goal: study Si surface reconstruction",
                "material: Si(001)",
                "software: vasp",
                "parameters: {\"encut\": 520, \"kppa\": 100, \"structure_type\": \"diamond\", \"lattice_param\": 5.43, \"elements\": [\"Si\"]}",
                "pdfs: papers/surface.pdf",
                "bibtex: refs/references.bib",
                "dois: 10.1000/alpha",
            ]),
            output_dir=tmpdir,
        )

        result = run_pipeline(str(project_root / ".simflow"), target_stage="compute", dry_run=False)
        workflow = read_state(tmpdir, "workflow.json")
        stages_state = read_state(tmpdir, "stages.json")
        input_generation_artifacts = list_artifacts(stage="input_generation", project_root=tmpdir)
        compute_artifacts = list_artifacts(stage="compute", project_root=tmpdir)

        assert result["status"] == "success"
        assert [item["stage"] for item in result["results"]] == ["literature", "review", "proposal", "modeling", "input_generation", "compute"]
        assert workflow["current_stage"] == "compute"
        assert workflow["status"] == "in_progress"
        assert stages_state["input_generation"]["status"] == "completed"
        assert stages_state["compute"]["status"] == "completed"
        assert any(artifact["name"] == "input_manifest.json" for artifact in input_generation_artifacts)
        assert {artifact["name"] for artifact in compute_artifacts} == {"compute_plan.json", "job_script.sh", "dry_run_report.json"}
        assert (project_root / ".simflow" / "artifacts" / "input_generation" / "INCAR").is_file()
        assert (project_root / ".simflow" / "artifacts" / "input_generation" / "KPOINTS").is_file()
        assert (project_root / ".simflow" / "reports" / "input_generation" / "input_manifest.json").is_file()
        assert (project_root / ".simflow" / "reports" / "compute" / "compute_plan.json").is_file()
        assert (project_root / ".simflow" / "reports" / "compute" / "dry_run_report.json").is_file()
        assert (project_root / ".simflow" / "artifacts" / "compute" / "job_script.sh").is_file()


@pytest.mark.skipif(not H2O_CIF.exists(), reason="H2O.cif not available")
def test_run_pipeline_execute_runs_precompute_cp2k_chain():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        pdf_path = project_root / "papers" / "surface.pdf"
        bib_path = project_root / "refs" / "references.bib"
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        bib_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_path.write_text("pdf placeholder", encoding="utf-8")
        bib_path.write_text("@article{water, title={Water Study}}", encoding="utf-8")

        init_research(
            input_text="\n".join([
                "goal: study liquid water energetics",
                "material: H2O",
                "software: cp2k",
                f"parameters: {{\"task\": \"energy\", \"structure_file\": \"{H2O_CIF}\"}}",
                "pdfs: papers/surface.pdf",
                "bibtex: refs/references.bib",
                "dois: 10.1000/beta",
            ]),
            output_dir=tmpdir,
        )

        result = run_pipeline(str(project_root / ".simflow"), target_stage="compute", dry_run=False)
        workflow = read_state(tmpdir, "workflow.json")
        compute_artifacts = list_artifacts(stage="compute", project_root=tmpdir)

        assert result["status"] == "success"
        assert [item["stage"] for item in result["results"]] == ["literature", "review", "proposal", "modeling", "input_generation", "compute"]
        assert workflow["current_stage"] == "compute"
        assert {artifact["name"] for artifact in compute_artifacts} == {"compute_plan.json", "job_script.sh", "dry_run_report.json"}
        assert (project_root / ".simflow" / "artifacts" / "input_generation" / "energy.inp").is_file()
        assert (project_root / ".simflow" / "artifacts" / "input_generation" / "structure.xyz").is_file()
        assert (project_root / ".simflow" / "reports" / "input_generation" / "input_manifest.json").is_file()
        assert (project_root / ".simflow" / "reports" / "compute" / "compute_plan.json").is_file()
        assert (project_root / ".simflow" / "artifacts" / "compute" / "job_script.sh").is_file()



def test_run_pipeline_execute_runs_postcompute_vasp_chain_without_outputs():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        pdf_path = project_root / "papers" / "surface.pdf"
        bib_path = project_root / "refs" / "references.bib"
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        bib_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_path.write_text("pdf placeholder", encoding="utf-8")
        bib_path.write_text("@article{surface, title={Surface Study}}", encoding="utf-8")

        init_research(
            input_text="\n".join([
                "goal: study Si surface reconstruction",
                "material: Si(001)",
                "software: vasp",
                "parameters: {\"encut\": 520, \"kppa\": 100, \"structure_type\": \"diamond\", \"lattice_param\": 5.43, \"elements\": [\"Si\"]}",
                "pdfs: papers/surface.pdf",
                "bibtex: refs/references.bib",
                "dois: 10.1000/alpha",
            ]),
            output_dir=tmpdir,
        )

        precompute_result = run_pipeline(str(project_root / ".simflow"), target_stage="compute", dry_run=False)
        result = run_pipeline(str(project_root / ".simflow"), target_stage="visualization", dry_run=False)
        workflow = read_state(tmpdir, "workflow.json")
        stages_state = read_state(tmpdir, "stages.json")
        analysis_artifacts = list_artifacts(stage="analysis", project_root=tmpdir)
        visualization_artifacts = list_artifacts(stage="visualization", project_root=tmpdir)

        assert precompute_result["status"] == "success"
        assert result["status"] == "success"
        assert [item["stage"] for item in result["results"]] == ["analysis", "visualization"]
        assert workflow["current_stage"] == "visualization"
        assert workflow["status"] == "in_progress"
        assert stages_state["analysis"]["status"] == "completed"
        assert stages_state["visualization"]["status"] == "completed"
        assert result["results"][0]["manifest"]["status"] == "waiting_for_outputs"
        assert result["results"][1]["manifest"]["status"] == "waiting_for_outputs"
        assert {artifact["name"] for artifact in analysis_artifacts} == {"analysis_report.json", "analysis_report.md"}
        assert {artifact["name"] for artifact in visualization_artifacts} == {"figures_manifest.json"}



def test_run_pipeline_execute_runs_postcompute_vasp_chain_with_fixture_outputs():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        pdf_path = project_root / "papers" / "surface.pdf"
        bib_path = project_root / "refs" / "references.bib"
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        bib_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_path.write_text("pdf placeholder", encoding="utf-8")
        bib_path.write_text("@article{surface, title={Surface Study}}", encoding="utf-8")

        init_research(
            input_text="\n".join([
                "goal: study Si surface reconstruction",
                "material: Si(001)",
                "software: vasp",
                "parameters: {\"encut\": 520, \"kppa\": 100, \"structure_type\": \"diamond\", \"lattice_param\": 5.43, \"elements\": [\"Si\"]}",
                "pdfs: papers/surface.pdf",
                "bibtex: refs/references.bib",
                "dois: 10.1000/alpha",
            ]),
            output_dir=tmpdir,
        )

        precompute_result = run_pipeline(str(project_root / ".simflow"), target_stage="compute", dry_run=False)
        compute_dir = project_root / ".simflow" / "artifacts" / "compute"
        shutil.copy2(VASP_RUN_XML, compute_dir / "vasprun.xml")
        (compute_dir / "OSZICAR").write_text(
            " 1 F= -.100000 E0= -.100000 d E =0.000000\n 2 F= -.200000 E0= -.200000 d E =0.000000\n",
            encoding="utf-8",
        )

        result = run_pipeline(str(project_root / ".simflow"), target_stage="visualization", dry_run=False)
        analysis_artifacts = list_artifacts(stage="analysis", project_root=tmpdir)
        visualization_artifacts = list_artifacts(stage="visualization", project_root=tmpdir)

        assert precompute_result["status"] == "success"
        assert result["status"] == "success"
        assert [item["stage"] for item in result["results"]] == ["analysis", "visualization"]
        assert result["results"][0]["manifest"]["status"] == "completed"
        assert result["results"][0]["manifest"]["source_files"]
        if importlib.util.find_spec("matplotlib") is None:
            assert result["results"][1]["manifest"]["status"] == "skipped_optional_dependency"
            assert {artifact["name"] for artifact in visualization_artifacts} == {"figures_manifest.json"}
        else:
            assert result["results"][1]["manifest"]["status"] == "completed"
            assert {artifact["name"] for artifact in visualization_artifacts} == {"figures_manifest.json", "energy_convergence.png"}
            assert (project_root / ".simflow" / "artifacts" / "visualization" / "energy_convergence.png").is_file()
        assert {artifact["name"] for artifact in analysis_artifacts} == {"analysis_report.json", "analysis_report.md"}


def test_run_pipeline_execute_runs_writing_stage_from_visualization_outputs():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        pdf_path = project_root / "papers" / "surface.pdf"
        bib_path = project_root / "refs" / "references.bib"
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        bib_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_path.write_text("pdf placeholder", encoding="utf-8")
        bib_path.write_text("@article{surface, title={Surface Study}}", encoding="utf-8")

        init_research(
            input_text="\n".join([
                "goal: study Si surface reconstruction",
                "material: Si(001)",
                "software: vasp",
                "parameters: {\"encut\": 520, \"kppa\": 100, \"structure_type\": \"diamond\", \"lattice_param\": 5.43, \"elements\": [\"Si\"]}",
                "pdfs: papers/surface.pdf",
                "bibtex: refs/references.bib",
                "dois: 10.1000/alpha",
            ]),
            output_dir=tmpdir,
        )

        precompute_result = run_pipeline(str(project_root / ".simflow"), target_stage="compute", dry_run=False)
        postcompute_result = run_pipeline(str(project_root / ".simflow"), target_stage="visualization", dry_run=False)
        result = run_pipeline(str(project_root / ".simflow"), target_stage="writing", dry_run=False)
        workflow = read_state(tmpdir, "workflow.json")
        stages_state = read_state(tmpdir, "stages.json")
        writing_artifacts = list_artifacts(stage="writing", project_root=tmpdir)
        results_path = project_root / ".simflow" / "reports" / "writing" / "results.md"
        reproducibility_package_path = project_root / ".simflow" / "reports" / "reproducibility" / "reproducibility_package.md"

        assert precompute_result["status"] == "success"
        assert postcompute_result["status"] == "success"
        assert result["status"] == "success"
        assert [item["stage"] for item in result["results"]] == ["writing"]
        assert result["results"][0]["manifest"]["analysis_status"] == "waiting_for_outputs"
        assert result["results"][0]["manifest"]["visualization_status"] == "waiting_for_outputs"
        assert workflow["current_stage"] == "writing"
        assert workflow["status"] == "completed"
        assert stages_state["writing"]["status"] == "completed"
        assert len(stages_state["writing"]["inputs"]) == 7
        assert len(stages_state["writing"]["outputs"]) == 4
        assert {artifact["name"] for artifact in writing_artifacts} == {
            "methods.md",
            "results.md",
            "reproducibility_package.md",
            "reproducibility_manifest.json",
        }
        assert results_path.is_file()
        assert reproducibility_package_path.is_file()
        assert "degraded or waiting" in results_path.read_text(encoding="utf-8")


@pytest.mark.skipif(not H2O_CIF.exists(), reason="H2O.cif not available")
def test_run_pipeline_execute_runs_postcompute_cp2k_md_chain_with_fixture_outputs():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        pdf_path = project_root / "papers" / "surface.pdf"
        bib_path = project_root / "refs" / "references.bib"
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        bib_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_path.write_text("pdf placeholder", encoding="utf-8")
        bib_path.write_text("@article{water, title={Water Study}}", encoding="utf-8")

        init_research(
            input_text="\n".join([
                "goal: study liquid water dynamics",
                "material: H2O",
                "software: cp2k",
                f"parameters: {{\"task\": \"aimd_nvt\", \"structure_file\": \"{H2O_CIF}\"}}",
                "pdfs: papers/surface.pdf",
                "bibtex: refs/references.bib",
                "dois: 10.1000/beta",
            ]),
            output_dir=tmpdir,
        )

        precompute_result = run_pipeline(str(project_root / ".simflow"), target_stage="compute", dry_run=False)
        compute_dir = project_root / ".simflow" / "artifacts" / "compute"
        for fixture_name in ("md.log", "md.ener", "md-pos-1.xyz", "md.restart"):
            shutil.copy2(CP2K_FIXTURE_DIR / fixture_name, compute_dir / fixture_name)

        result = run_pipeline(str(project_root / ".simflow"), target_stage="visualization", dry_run=False)
        analysis_artifacts = list_artifacts(stage="analysis", project_root=tmpdir)
        visualization_artifacts = list_artifacts(stage="visualization", project_root=tmpdir)
        trajectory_status = result["results"][0]["manifest"]["optional_trajectory_analysis"]["status"]

        assert precompute_result["status"] == "success"
        assert result["status"] == "success"
        assert [item["stage"] for item in result["results"]] == ["analysis", "visualization"]
        assert result["results"][0]["manifest"]["status"] == "completed"
        assert result["results"][0]["manifest"]["source_files"]
        assert trajectory_status in {"available", "skipped_optional_dependency"}
        if importlib.util.find_spec("matplotlib") is None:
            assert result["results"][1]["manifest"]["status"] == "skipped_optional_dependency"
            assert {artifact["name"] for artifact in visualization_artifacts} == {"figures_manifest.json"}
        else:
            assert result["results"][1]["manifest"]["status"] == "completed"
            assert {artifact["name"] for artifact in visualization_artifacts} == {"figures_manifest.json", "energy_convergence.png"}
            assert (project_root / ".simflow" / "artifacts" / "visualization" / "energy_convergence.png").is_file()
        assert {artifact["name"] for artifact in analysis_artifacts} == {"analysis_report.json", "analysis_report.md"}
