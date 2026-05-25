#!/usr/bin/env python3
"""Tests for canonical pipeline behavior."""

import importlib.util
import json
import shutil
import sys
import tempfile
import hashlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from runtime.simflow_core.artifacts import list_artifacts
from runtime.simflow_core.gates import check_gate, record_gate_decision
from runtime.simflow_core.state import init_workflow, read_state, write_state
from runtime.simflow_helpers.stages.pipeline import run_pipeline
from runtime.simflow_helpers.project.intake import init_research

pytestmark = pytest.mark.filterwarnings(
    "ignore:Duplicate keys found.*ENCUT.*:pymatgen.io.vasp.inputs.BadIncarWarning"
)


DFT_STAGES = [
    "literature_review",
    "proposal",
    "modeling",
    "computation",
    "analysis_visualization",
    "writing",
]

H2O_CIF = ROOT / "examples" / "h2o" / "H2O.cif"
VASP_RUN_XML = ROOT / "tests" / "fixtures" / "vasprun_Si.xml"
CP2K_FIXTURE_DIR = ROOT / "tests" / "fixtures" / "cp2k"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_metadata(tmpdir: str):
    state = read_state(tmpdir, "workflow.json")
    metadata = {
        "workflow_id": state["workflow_id"],
        "workflow_type": "dft",
        "entry_point": "literature_review",
        "current_stage": "literature_review",
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
        assert [item["stage"] for item in result["results"]] == ["literature_review", "proposal"]
        assert all(item["status"] == "dry_run_complete" for item in result["results"])
        assert stages_state["literature_review"]["status"] == "pending"
        assert stages_state["proposal"]["status"] == "pending"
        assert "legacy_stage" not in stages_state
        assert not (Path(tmpdir) / ".simflow" / "workflow_state.json").exists()


def test_run_pipeline_execute_updates_stages_and_checkpoint_registry():
    with tempfile.TemporaryDirectory() as tmpdir:
        init_workflow("dft", "literature", tmpdir)
        _write_metadata(tmpdir)

        result = run_pipeline(str(Path(tmpdir) / ".simflow"), target_stage="literature_review", dry_run=False)
        workflow = read_state(tmpdir, "workflow.json")
        stages_state = read_state(tmpdir, "stages.json")
        checkpoints = read_state(tmpdir, "checkpoints.json")

        assert result["status"] == "success"
        assert [item["stage"] for item in result["results"]] == ["literature_review"]
        assert all(item["status"] == "completed" for item in result["results"])
        assert workflow["current_stage"] == "literature_review"
        assert workflow["status"] == "in_progress"
        assert stages_state["literature_review"]["status"] == "completed"
        assert "literature" not in stages_state
        assert "review" not in stages_state
        assert stages_state["literature_review"]["checkpoint_id"] == result["checkpoint_id"]
        assert len(checkpoints) == 1
        assert checkpoints[0]["checkpoint_id"] == result["checkpoint_id"]
        assert checkpoints[0]["stage_id"] == "literature_review"
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

        result = run_pipeline(str(Path(tmpdir) / ".simflow"), target_stage="analysis_visualization", dry_run=True)

        assert [item["stage"] for item in result["results"]] == ["computation", "analysis_visualization"]
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

        result = run_pipeline(str(project_root / ".simflow"), target_stage="literature_review", dry_run=False)
        workflow = read_state(tmpdir, "workflow.json")
        stages_state = read_state(tmpdir, "stages.json")
        literature_artifacts = list_artifacts(stage="literature_review", project_root=tmpdir)
        review_artifacts = list_artifacts(stage="literature_review", project_root=tmpdir)

        assert result["status"] == "success"
        assert [item["stage"] for item in result["results"]] == ["literature_review"]
        generated_names = {artifact["name"] for artifact in result["results"][0]["artifacts"]}
        assert "literature_matrix.json" in generated_names
        assert "review_summary.md" in generated_names
        assert workflow["current_stage"] == "literature_review"
        assert stages_state["literature_review"]["status"] == "completed"
        assert "literature" not in stages_state
        assert "review" not in stages_state
        assert {
            "literature_matrix.json",
            "literature_matrix.csv",
            "search_log.json",
            "screening_record.json",
            "citation_map.json",
            "review_summary.md",
            "gap_analysis.md",
        }.issubset({artifact["name"] for artifact in literature_artifacts})
        assert any(artifact["type"] == "paper_notes" for artifact in literature_artifacts)
        assert len(literature_artifacts) == len(review_artifacts)
        assert set(stages_state["literature_review"]["inputs"]).issubset(
            {artifact["artifact_id"] for artifact in literature_artifacts}
        )
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
        assert [item["stage"] for item in result["results"]] == ["literature_review", "proposal", "modeling"]
        assert result["results"][-1]["artifacts"][0]["name"] == "structure_manifest.json"
        assert workflow["current_stage"] == "modeling"
        assert workflow["status"] == "in_progress"
        assert stages_state["modeling"]["status"] == "completed"
        assert set(stages_state["modeling"]["inputs"]) == {artifact["artifact_id"] for artifact in proposal_artifacts}
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

        result = run_pipeline(str(project_root / ".simflow"), target_stage="computation", dry_run=False)
        workflow = read_state(tmpdir, "workflow.json")
        stages_state = read_state(tmpdir, "stages.json")
        input_generation_artifacts = list_artifacts(stage="computation", project_root=tmpdir)
        compute_artifacts = list_artifacts(stage="computation", project_root=tmpdir)

        assert result["status"] == "success"
        assert [item["stage"] for item in result["results"]] == ["literature_review", "proposal", "modeling", "computation"]
        assert workflow["current_stage"] == "computation"
        assert workflow["status"] == "in_progress"
        assert stages_state["computation"]["status"] == "completed"
        assert "input_generation" not in stages_state
        assert "compute" not in stages_state
        assert any(artifact["name"] == "input_manifest.json" for artifact in input_generation_artifacts)
        assert {"compute_plan.json", "job_script.sh", "dry_run_report.json"}.issubset({artifact["name"] for artifact in compute_artifacts})
        assert (project_root / ".simflow" / "artifacts" / "input_generation" / "INCAR").is_file()
        assert (project_root / ".simflow" / "artifacts" / "input_generation" / "KPOINTS").is_file()
        assert (project_root / ".simflow" / "reports" / "input_generation" / "input_manifest.json").is_file()
        assert (project_root / ".simflow" / "reports" / "compute" / "compute_plan.json").is_file()
        assert (project_root / ".simflow" / "reports" / "compute" / "dry_run_report.json").is_file()
        assert (project_root / ".simflow" / "artifacts" / "compute" / "job_script.sh").is_file()


def test_computation_stage_emits_hpc_submit_gate_evidence():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        init_research(
            input_text="\n".join([
                "goal: prepare a VASP dry-run evidence package",
                "material: Si",
                "software: vasp",
                "parameters: {\"encut\": 520, \"kppa\": 100, \"structure_type\": \"diamond\", \"lattice_param\": 5.43, \"elements\": [\"Si\"]}",
            ]),
            output_dir=tmpdir,
        )

        result = run_pipeline(str(project_root / ".simflow"), target_stage="computation", dry_run=False)
        artifacts = list_artifacts(stage="computation", project_root=tmpdir)
        artifact_names = {artifact["name"] for artifact in artifacts}
        artifact_types = {artifact["type"] for artifact in artifacts}
        compute_dir = project_root / ".simflow" / "artifacts" / "compute"
        security_dir = project_root / ".simflow" / "artifacts" / "security"
        dry_run_path = compute_dir / "dry_run_report.json"
        input_validation_path = compute_dir / "input_validation.json"
        resource_estimate_path = compute_dir / "resource_estimate.json"
        credential_scan_path = security_dir / "credential_scan.json"
        job_script_path = compute_dir / "job_script.sh"
        submit_readiness_summary_path = project_root / ".simflow" / "reports" / "compute" / "submit_readiness_summary.md"

        dry_run = json.loads(dry_run_path.read_text(encoding="utf-8"))
        input_validation = json.loads(input_validation_path.read_text(encoding="utf-8"))
        resource_estimate = json.loads(resource_estimate_path.read_text(encoding="utf-8"))
        credential_scan = json.loads(credential_scan_path.read_text(encoding="utf-8"))
        compute_result = result["results"][-1]
        submit_readiness = compute_result["manifests"]["compute"]["submit_readiness"]
        user_submit_readiness = compute_result["manifests"]["compute"]["user_submit_readiness"]

        assert result["status"] == "success"
        assert {
            "dry_run_report.json",
            "input_validation.json",
            "resource_estimate.json",
            "credential_scan.json",
            "submit_readiness_summary.md",
        }.issubset(artifact_names)
        assert {
            "dry_run_report",
            "input_validation_report",
            "resource_estimate",
            "credential_scan",
            "submit_readiness_summary",
        }.issubset(artifact_types)
        assert dry_run["status"] in {"pass", "warning"}
        assert dry_run["script_hash"] == _sha256_file(job_script_path)
        assert dry_run["input_artifact_hash"] == _sha256_file(project_root / ".simflow" / "reports" / "input_generation" / "input_manifest.json")
        assert input_validation["missing_required_files"] == []
        assert resource_estimate["status"] in {"pass", "warning"}
        assert credential_scan["findings"] == []
        assert submit_readiness["project_root"] == tmpdir
        assert submit_readiness["dry_run_evidence"] == "compute/dry_run_report.json"
        assert submit_readiness["script_hash"] == dry_run["script_hash"]
        assert submit_readiness["input_artifact_hash"] == dry_run["input_artifact_hash"]
        assert user_submit_readiness["ready_for_approval"] is True
        assert user_submit_readiness["real_submit_allowed"] is False
        assert user_submit_readiness["approval_required"] is True
        assert user_submit_readiness["failed_checks"] == []
        assert user_submit_readiness["evidence"]["dry_run_report"] == ".simflow/artifacts/compute/dry_run_report.json"
        assert submit_readiness_summary_path.is_file()
        assert "Real submit allowed: False" in submit_readiness_summary_path.read_text(encoding="utf-8")
        assert check_gate("hpc_submit", {"project_root": tmpdir})["status"] == "block"

        record_gate_decision(
            "hpc_submit",
            "approved",
            {"reason": "reviewed generated dry-run evidence"},
            project_root=tmpdir,
            agent="test_agent",
        )
        assert check_gate("hpc_submit", {"project_root": tmpdir})["status"] == "pass"


@pytest.mark.skipif(not H2O_CIF.exists(), reason="H2O.cif not available")
@pytest.mark.filterwarnings("ignore:Issues encountered while parsing CIF:UserWarning")
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

        result = run_pipeline(str(project_root / ".simflow"), target_stage="computation", dry_run=False)
        workflow = read_state(tmpdir, "workflow.json")
        compute_artifacts = list_artifacts(stage="computation", project_root=tmpdir)

        assert result["status"] == "success"
        assert [item["stage"] for item in result["results"]] == ["literature_review", "proposal", "modeling", "computation"]
        assert workflow["current_stage"] == "computation"
        assert {"compute_plan.json", "job_script.sh", "dry_run_report.json"}.issubset({artifact["name"] for artifact in compute_artifacts})
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

        precompute_result = run_pipeline(str(project_root / ".simflow"), target_stage="computation", dry_run=False)
        result = run_pipeline(str(project_root / ".simflow"), target_stage="analysis_visualization", dry_run=False)
        workflow = read_state(tmpdir, "workflow.json")
        stages_state = read_state(tmpdir, "stages.json")
        analysis_artifacts = list_artifacts(stage="analysis_visualization", project_root=tmpdir)
        visualization_artifacts = list_artifacts(stage="analysis_visualization", project_root=tmpdir)

        assert precompute_result["status"] == "success"
        assert result["status"] == "success"
        assert [item["stage"] for item in result["results"]] == ["analysis_visualization"]
        assert workflow["current_stage"] == "analysis_visualization"
        assert workflow["status"] == "in_progress"
        assert stages_state["analysis_visualization"]["status"] == "completed"
        assert "analysis" not in stages_state
        assert "visualization" not in stages_state
        assert result["results"][0]["manifest"]["status"] == "waiting_for_outputs"
        assert {artifact["name"] for artifact in analysis_artifacts} == {
            "analysis_report.json",
            "analysis_report.md",
            "figures_manifest.json",
        }
        assert {artifact["name"] for artifact in visualization_artifacts} == {
            "analysis_report.json",
            "analysis_report.md",
            "figures_manifest.json",
        }



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

        precompute_result = run_pipeline(str(project_root / ".simflow"), target_stage="computation", dry_run=False)
        compute_dir = project_root / ".simflow" / "artifacts" / "compute"
        shutil.copy2(VASP_RUN_XML, compute_dir / "vasprun.xml")
        (compute_dir / "OSZICAR").write_text(
            " 1 F= -.100000 E0= -.100000 d E =0.000000\n 2 F= -.200000 E0= -.200000 d E =0.000000\n",
            encoding="utf-8",
        )

        result = run_pipeline(str(project_root / ".simflow"), target_stage="analysis_visualization", dry_run=False)
        analysis_artifacts = list_artifacts(stage="analysis_visualization", project_root=tmpdir)
        visualization_artifacts = list_artifacts(stage="analysis_visualization", project_root=tmpdir)

        assert precompute_result["status"] == "success"
        assert result["status"] == "success"
        assert [item["stage"] for item in result["results"]] == ["analysis_visualization"]
        assert result["results"][0]["manifests"]["analysis"]["status"] == "completed"
        assert result["results"][0]["manifests"]["analysis"]["source_files"]
        assert result["results"][0]["manifests"]["analysis"]["analysis_provenance"]["input_artifact_ids"]
        assert result["results"][0]["manifests"]["analysis"]["analysis_provenance"]["analysis_script"].endswith("analyze_dft_results.py")
        assert result["results"][0]["manifests"]["visualization"]["figure_traceability"]["analysis_report_artifact_id"]
        if importlib.util.find_spec("matplotlib") is None:
            assert result["results"][0]["manifests"]["visualization"]["status"] == "skipped_optional_dependency"
            assert {artifact["name"] for artifact in visualization_artifacts} == {
                "analysis_report.json",
                "analysis_report.md",
                "figures_manifest.json",
            }
        else:
            assert result["results"][0]["manifests"]["visualization"]["status"] == "completed"
            assert {artifact["name"] for artifact in visualization_artifacts} == {
                "analysis_report.json",
                "analysis_report.md",
                "figures_manifest.json",
                "energy_convergence.png",
            }
            assert (project_root / ".simflow" / "artifacts" / "visualization" / "energy_convergence.png").is_file()
            figure = result["results"][0]["manifests"]["visualization"]["figures"][0]
            assert figure["source_data"].endswith("OSZICAR")
            assert figure["plotting_script"].endswith("plot_energy_curve.py")
            assert result["results"][0]["manifests"]["visualization"]["figure_traceability"]["figures"][0]["name"] == "energy_convergence.png"
        assert {"analysis_report.json", "analysis_report.md"}.issubset({artifact["name"] for artifact in analysis_artifacts})


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

        precompute_result = run_pipeline(str(project_root / ".simflow"), target_stage="computation", dry_run=False)
        postcompute_result = run_pipeline(str(project_root / ".simflow"), target_stage="analysis_visualization", dry_run=False)
        result = run_pipeline(str(project_root / ".simflow"), target_stage="writing", dry_run=False)
        workflow = read_state(tmpdir, "workflow.json")
        stages_state = read_state(tmpdir, "stages.json")
        writing_artifacts = list_artifacts(stage="writing", project_root=tmpdir)
        results_path = project_root / ".simflow" / "reports" / "writing" / "results.md"
        claim_map_path = project_root / ".simflow" / "reports" / "writing" / "claim_map.json"
        reproducibility_package_path = project_root / ".simflow" / "reports" / "reproducibility" / "reproducibility_package.md"
        final_handoff_markdown_path = project_root / ".simflow" / "reports" / "handoff" / "final_handoff.md"
        final_handoff_json_path = project_root / ".simflow" / "reports" / "handoff" / "final_handoff.json"

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
        assert len(stages_state["writing"]["outputs"]) == 6
        assert {artifact["name"] for artifact in writing_artifacts} == {
            "methods.md",
            "results.md",
            "claim_map.json",
            "reproducibility_package.md",
            "reproducibility_manifest.json",
            "final_handoff.md",
            "final_handoff.json",
            "verification_report.json",
        }
        stage_output_names = {
            artifact["name"]
            for artifact in writing_artifacts
            if artifact["artifact_id"] in stages_state["writing"]["outputs"]
        }
        assert stage_output_names == {
            "methods.md",
            "results.md",
            "claim_map.json",
            "reproducibility_package.md",
            "final_handoff.md",
            "final_handoff.json",
        }
        assert results_path.is_file()
        assert claim_map_path.is_file()
        assert reproducibility_package_path.is_file()
        assert final_handoff_markdown_path.is_file()
        assert final_handoff_json_path.is_file()
        claim_map = json.loads(claim_map_path.read_text(encoding="utf-8"))
        assert claim_map["claim_policy"].startswith("Scientific claims must trace")
        assert any(claim["status"] == "waiting_for_outputs" and claim["speculative"] for claim in claim_map["claims"])
        assert "degraded or waiting" in results_path.read_text(encoding="utf-8")


@pytest.mark.skipif(not H2O_CIF.exists(), reason="H2O.cif not available")
@pytest.mark.filterwarnings("ignore:Issues encountered while parsing CIF:UserWarning")
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

        precompute_result = run_pipeline(str(project_root / ".simflow"), target_stage="computation", dry_run=False)
        compute_dir = project_root / ".simflow" / "artifacts" / "compute"
        for fixture_name in ("md.log", "md.ener", "md-pos-1.xyz", "md.restart"):
            shutil.copy2(CP2K_FIXTURE_DIR / fixture_name, compute_dir / fixture_name)

        result = run_pipeline(str(project_root / ".simflow"), target_stage="analysis_visualization", dry_run=False)
        analysis_artifacts = list_artifacts(stage="analysis_visualization", project_root=tmpdir)
        visualization_artifacts = list_artifacts(stage="analysis_visualization", project_root=tmpdir)
        trajectory_status = result["results"][0]["manifests"]["analysis"]["optional_trajectory_analysis"]["status"]

        assert precompute_result["status"] == "success"
        assert result["status"] == "success"
        assert [item["stage"] for item in result["results"]] == ["analysis_visualization"]
        assert result["results"][0]["manifests"]["analysis"]["status"] == "completed"
        assert result["results"][0]["manifests"]["analysis"]["source_files"]
        assert result["results"][0]["manifests"]["analysis"]["analysis_provenance"]["analysis_script"] == "runtime/simflow_helpers/engines/cp2k"
        assert result["results"][0]["manifests"]["visualization"]["figure_traceability"]["source_files"]
        assert trajectory_status in {"available", "skipped_optional_dependency"}
        if importlib.util.find_spec("matplotlib") is None:
            assert result["results"][0]["manifests"]["visualization"]["status"] == "skipped_optional_dependency"
            assert {artifact["name"] for artifact in visualization_artifacts} == {
                "analysis_report.json",
                "analysis_report.md",
                "figures_manifest.json",
            }
        else:
            assert result["results"][0]["manifests"]["visualization"]["status"] == "completed"
            assert {artifact["name"] for artifact in visualization_artifacts} == {
                "analysis_report.json",
                "analysis_report.md",
                "figures_manifest.json",
                "energy_convergence.png",
            }
            assert (project_root / ".simflow" / "artifacts" / "visualization" / "energy_convergence.png").is_file()
            figure = result["results"][0]["manifests"]["visualization"]["figures"][0]
            assert figure["source_data"].endswith(".ener")
            assert result["results"][0]["manifests"]["visualization"]["figure_traceability"]["figures"][0]["name"] == "energy_convergence.png"
        assert {"analysis_report.json", "analysis_report.md"}.issubset({artifact["name"] for artifact in analysis_artifacts})
