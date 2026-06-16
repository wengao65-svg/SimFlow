#!/usr/bin/env python3
"""Tests for canonical stage executor behavior."""

import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from runtime.simflow_core.artifacts import list_artifacts
from runtime.simflow_core.state import init_workflow, read_state, write_state
from runtime.simflow_helpers.stages.executor import execute_stage
from runtime.simflow_helpers.project.intake import init_research
from runtime.simflow_helpers.stages.pipeline import run_pipeline


VASP_RUN_XML = ROOT / "tests" / "fixtures" / "vasprun_Si.xml"
CP2K_FIXTURE_DIR = ROOT / "tests" / "fixtures" / "cp2k"

pytestmark = pytest.mark.filterwarnings(
    "ignore:Duplicate keys found.*ENCUT.*:pymatgen.io.vasp.inputs.BadIncarWarning"
)


def _write_metadata(tmpdir: str, workflow_type: str = "dft"):
    state = read_state(tmpdir, "workflow.json")
    metadata = {
        "workflow_id": state["workflow_id"],
        "workflow_type": workflow_type,
        "entry_point": "literature_review" if workflow_type == "dft" else "proposal",
        "current_stage": "literature_review" if workflow_type == "dft" else "proposal",
        "stages": [],
    }
    write_state(metadata, project_root=tmpdir, state_file="metadata.json")


def test_execute_stage_dry_run_uses_workflow_definition_not_workflow_json_stages():
    with tempfile.TemporaryDirectory() as tmpdir:
        init_workflow("dft", "literature", tmpdir)
        _write_metadata(tmpdir, "dft")
        workflow = read_state(tmpdir, "workflow.json")
        workflow["stages"] = ["legacy_stage"]
        write_state(workflow, project_root=tmpdir, state_file="workflow.json")

        result = execute_stage(str(Path(tmpdir) / ".simflow"), "literature_review", dry_run=True)
        stages_state = read_state(tmpdir, "stages.json")

        assert result["status"] == "dry_run_complete"
        assert result["stage"] == "literature_review"
        assert stages_state["literature_review"]["status"] == "pending"
        assert "legacy_stage" not in stages_state
        assert not (Path(tmpdir) / ".simflow" / "workflow_state.json").exists()


def test_execute_stage_rejects_stage_not_in_workflow_definition():
    with tempfile.TemporaryDirectory() as tmpdir:
        init_workflow("aimd", "proposal", tmpdir)
        _write_metadata(tmpdir, "aimd")

        result = execute_stage(str(Path(tmpdir) / ".simflow"), "literature_review", dry_run=True)
        stages_state = read_state(tmpdir, "stages.json")

        assert result["status"] == "error"
        assert result["message"] == "Unknown stage: literature_review"
        assert stages_state == {}


def test_execute_stage_execute_runs_modeling_runner_and_registers_artifacts():
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
        pipeline_result = run_pipeline(str(project_root / ".simflow"), target_stage="proposal", dry_run=False)

        result = execute_stage(str(project_root / ".simflow"), "modeling", params={"supercell": "2x2x1"}, dry_run=False)
        workflow = read_state(tmpdir, "workflow.json")
        stages_state = read_state(tmpdir, "stages.json")
        proposal_artifacts = list_artifacts(stage="proposal", project_root=tmpdir)
        modeling_artifacts = list_artifacts(stage="modeling", project_root=tmpdir)

        assert pipeline_result["status"] == "success"
        assert result["status"] == "completed"
        assert result["params"] == {"supercell": "2x2x1"}
        assert result["manifest"]["source_mode"] == "from_type"
        assert result["manifest"]["supercell"] == [2, 2, 1]
        assert result["manifest"]["structure_files"] == [".simflow/artifacts/modeling/POSCAR_supercell"]
        assert workflow["current_stage"] == "modeling"
        assert workflow["status"] == "in_progress"
        assert stages_state["modeling"]["status"] == "completed"
        assert set(stages_state["modeling"]["inputs"]) == {artifact["artifact_id"] for artifact in proposal_artifacts}
        assert len(stages_state["modeling"]["outputs"]) == 2
        assert result["scripts"][0]["status"] == "executed"
        assert {artifact["name"] for artifact in modeling_artifacts} == {"structure_manifest.json", "POSCAR_supercell"}
        assert (project_root / ".simflow" / "reports" / "modeling" / "structure_manifest.json").is_file()
        assert (project_root / ".simflow" / "artifacts" / "modeling" / "POSCAR_supercell").is_file()
        assert not (Path(tmpdir) / ".simflow" / "workflow_state.json").exists()
        assert not (Path(tmpdir) / ".simflow" / "metadata.json").exists()


def test_modeling_runner_registers_user_provided_structure_source():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        source_poscar = project_root / "inputs" / "POSCAR"
        pdf_path = project_root / "papers" / "surface.pdf"
        bib_path = project_root / "refs" / "references.bib"
        source_poscar.parent.mkdir(parents=True, exist_ok=True)
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        bib_path.parent.mkdir(parents=True, exist_ok=True)
        source_poscar.write_text(
            "Si\n1.0\n3.0 0.0 0.0\n0.0 3.0 0.0\n0.0 0.0 3.0\nSi\n1\nDirect\n0.0 0.0 0.0\n",
            encoding="utf-8",
        )
        pdf_path.write_text("pdf placeholder", encoding="utf-8")
        bib_path.write_text("@article{surface, title={Surface Study}}", encoding="utf-8")

        init_research(
            input_text="\n".join([
                "goal: study user-provided Si structure",
                "material: Si",
                "software: vasp",
                "parameters: {\"structure_file\": \"inputs/POSCAR\", \"encut\": 520}",
                "pdfs: papers/surface.pdf",
                "bibtex: refs/references.bib",
            ]),
            output_dir=tmpdir,
        )
        pipeline_result = run_pipeline(str(project_root / ".simflow"), target_stage="proposal", dry_run=False)

        result = execute_stage(str(project_root / ".simflow"), "modeling", dry_run=False)
        modeling_artifacts = list_artifacts(stage="modeling", project_root=tmpdir)
        source_artifact = next(artifact for artifact in modeling_artifacts if artifact["type"] == "user_provided_structure")
        structure_artifact = next(artifact for artifact in modeling_artifacts if artifact["type"] == "structure")
        manifest_artifact = next(artifact for artifact in modeling_artifacts if artifact["type"] == "structure_manifest")

        assert pipeline_result["status"] == "success"
        assert result["status"] == "completed"
        assert result["manifest"]["source_mode"] == "existing_file"
        assert result["manifest"]["source_structure"]["registry_path"] == "inputs/POSCAR"
        assert result["manifest"]["source_structure"]["preserved_original"] is True
        assert result["manifest"]["source_structure"]["artifact_id"] == source_artifact["artifact_id"]
        assert source_artifact["path"] == "inputs/POSCAR"
        assert source_artifact["metadata"]["source"] == "user_provided"
        assert source_artifact["metadata"]["preserve_original"] is True
        assert source_poscar.read_text(encoding="utf-8").startswith("Si\n1.0")
        assert source_artifact["artifact_id"] in manifest_artifact["lineage"]["parent_artifacts"]
        assert source_artifact["artifact_id"] in structure_artifact["lineage"]["parent_artifacts"]


def test_execute_stage_allows_direct_modeling_entry_with_user_structure():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        source_poscar = project_root / "inputs" / "POSCAR"
        source_poscar.parent.mkdir(parents=True, exist_ok=True)
        source_poscar.write_text(
            "Si\n1.0\n3.0 0.0 0.0\n0.0 3.0 0.0\n0.0 0.0 3.0\nSi\n1\nDirect\n0.0 0.0 0.0\n",
            encoding="utf-8",
        )
        init_research(
            input_text="\n".join([
                "entry_stage: modeling",
                "goal: preserve a user-provided Si model",
                "material: Si",
                "software: vasp",
                "parameters: {\"structure_file\": \"inputs/POSCAR\"}",
            ]),
            output_dir=tmpdir,
        )

        result = execute_stage(str(project_root / ".simflow"), "modeling", dry_run=False)
        workflow = read_state(tmpdir, "workflow.json")
        stages_state = read_state(tmpdir, "stages.json")
        proposal_artifacts = list_artifacts(stage="proposal", project_root=tmpdir)
        modeling_artifacts = list_artifacts(stage="modeling", project_root=tmpdir)

        assert result["status"] == "completed"
        assert result["manifest"]["source_mode"] == "existing_file"
        assert result["manifest"]["proposal_artifact_ids"] == []
        assert proposal_artifacts == []
        assert workflow["current_stage"] == "modeling"
        assert {artifact["type"] for artifact in modeling_artifacts} == {
            "user_provided_structure",
            "structure_manifest",
            "structure",
        }
        source_artifact = next(artifact for artifact in modeling_artifacts if artifact["path"] == "inputs/POSCAR")
        assert source_artifact["artifact_id"] in stages_state["modeling"]["inputs"]



def test_execute_stage_execute_runs_input_generation_runner_and_registers_artifacts():
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
        pipeline_result = run_pipeline(str(project_root / ".simflow"), target_stage="modeling", dry_run=False)

        result = execute_stage(str(project_root / ".simflow"), "computation", dry_run=False)
        workflow = read_state(tmpdir, "workflow.json")
        stages_state = read_state(tmpdir, "stages.json")
        modeling_artifacts = list_artifacts(stage="modeling", project_root=tmpdir)
        input_generation_artifacts = list_artifacts(stage="computation", project_root=tmpdir)

        assert pipeline_result["status"] == "success"
        assert result["status"] == "completed"
        assert result["manifests"]["input_generation"]["software"] == "vasp"
        assert result["manifests"]["input_generation"]["task"] == "scf"
        assert result["manifests"]["input_generation"]["missing_optional_inputs"] == ["POTCAR"]
        assert workflow["current_stage"] == "computation"
        assert workflow["status"] == "in_progress"
        assert stages_state["computation"]["status"] == "completed"
        assert "input_generation" not in stages_state
        assert set(stages_state["computation"]["inputs"]) >= {artifact["artifact_id"] for artifact in modeling_artifacts}
        assert any(artifact["name"] == "input_manifest.json" for artifact in input_generation_artifacts)
        assert (project_root / ".simflow" / "artifacts" / "input_generation" / "INCAR").is_file()
        assert (project_root / ".simflow" / "artifacts" / "input_generation" / "KPOINTS").is_file()
        assert (project_root / ".simflow" / "reports" / "input_generation" / "input_manifest.json").is_file()



def test_execute_stage_execute_runs_compute_runner_and_registers_artifacts():
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
        pipeline_result = run_pipeline(str(project_root / ".simflow"), target_stage="modeling", dry_run=False)

        result = execute_stage(str(project_root / ".simflow"), "computation", dry_run=False)
        workflow = read_state(tmpdir, "workflow.json")
        stages_state = read_state(tmpdir, "stages.json")
        input_generation_artifacts = list_artifacts(stage="computation", project_root=tmpdir)
        compute_artifacts = list_artifacts(stage="computation", project_root=tmpdir)

        assert pipeline_result["status"] == "success"
        assert result["status"] == "completed"
        assert result["manifest"]["software"] == "vasp"
        assert result["manifest"]["dry_run"] is True
        assert result["manifest"]["real_submit"] is False
        assert workflow["current_stage"] == "computation"
        assert workflow["status"] == "in_progress"
        assert stages_state["computation"]["status"] == "completed"
        assert "compute" not in stages_state
        assert set(stages_state["computation"]["inputs"]) >= {artifact["artifact_id"] for artifact in input_generation_artifacts if artifact["name"] == "input_manifest.json"}
        assert {"compute_plan.json", "job_script.sh", "dry_run_report.json"}.issubset({artifact["name"] for artifact in compute_artifacts})
        assert (project_root / ".simflow" / "reports" / "compute" / "compute_plan.json").is_file()
        assert (project_root / ".simflow" / "reports" / "compute" / "dry_run_report.json").is_file()
        assert (project_root / ".simflow" / "artifacts" / "compute" / "job_script.sh").is_file()
        assert not (Path(tmpdir) / ".simflow" / "workflow_state.json").exists()
        assert not (Path(tmpdir) / ".simflow" / "metadata.json").exists()


def test_execute_stage_allows_direct_computation_entry_with_existing_inputs():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        inputs_dir = project_root / "inputs" / "vasp"
        inputs_dir.mkdir(parents=True, exist_ok=True)
        (inputs_dir / "INCAR").write_text("ENCUT = 520\n", encoding="utf-8")
        (inputs_dir / "KPOINTS").write_text("Gamma\n0\nGamma\n1 1 1\n0 0 0\n", encoding="utf-8")
        (inputs_dir / "POSCAR").write_text(
            "Si\n1.0\n3.0 0.0 0.0\n0.0 3.0 0.0\n0.0 0.0 3.0\nSi\n1\nDirect\n0.0 0.0 0.0\n",
            encoding="utf-8",
        )
        init_research(
            input_text="\n".join([
                "entry_stage: computation",
                "goal: dry-run existing VASP inputs",
                "material: Si",
                "software: vasp",
                "parameters: {\"input_files\": [\"inputs/vasp/INCAR\", \"inputs/vasp/KPOINTS\", \"inputs/vasp/POSCAR\"], \"task\": \"static\"}",
            ]),
            output_dir=tmpdir,
        )

        result = execute_stage(str(project_root / ".simflow"), "computation", dry_run=False)
        artifacts = list_artifacts(stage="computation", project_root=tmpdir)
        input_manifest = result["manifests"]["input_generation"]
        compute_manifest = result["manifests"]["compute"]

        assert result["status"] == "completed"
        assert input_manifest["source"] == "user_provided_input_files"
        assert input_manifest["generated_files"] == [
            "inputs/vasp/INCAR",
            "inputs/vasp/KPOINTS",
            "inputs/vasp/POSCAR",
        ]
        assert input_manifest["missing_optional_inputs"] == ["POTCAR"]
        assert compute_manifest["dry_run"] is True
        assert compute_manifest["real_submit"] is False
        assert compute_manifest["approval_required_for_real_submit"] is True
        assert compute_manifest["readiness_status"] == "pass"
        assert {"input_manifest.json", "compute_plan.json", "dry_run_report.json"}.issubset(
            {artifact["name"] for artifact in artifacts}
        )


def test_execute_stage_allows_direct_lammps_computation_entry_with_existing_inputs():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        inputs_dir = project_root / "inputs" / "lammps"
        inputs_dir.mkdir(parents=True, exist_ok=True)
        (inputs_dir / "in.lammps").write_text(
            "\n".join([
                "units metal",
                "atom_style atomic",
                "read_data data.lammps",
                "pair_style lj/cut 2.5",
                "pair_coeff * * 1.0 1.0",
                "run 0",
                "",
            ]),
            encoding="utf-8",
        )
        (inputs_dir / "data.lammps").write_text(
            "\n".join([
                "LAMMPS data file",
                "",
                "1 atoms",
                "1 atom types",
                "",
                "0.0 1.0 xlo xhi",
                "0.0 1.0 ylo yhi",
                "0.0 1.0 zlo zhi",
                "",
                "Masses",
                "",
                "1 28.0855",
                "",
                "Atoms # atomic",
                "",
                "1 1 0.0 0.0 0.0",
                "",
            ]),
            encoding="utf-8",
        )
        init_research(
            input_text="\n".join([
                "entry_stage: computation",
                "goal: dry-run existing LAMMPS inputs",
                "material: Si",
                "software: lammps",
                "parameters: {\"input_files\": [\"inputs/lammps/in.lammps\", \"inputs/lammps/data.lammps\"], \"task\": \"nvt\", \"num_atoms\": 1}",
            ]),
            output_dir=tmpdir,
        )

        result = execute_stage(str(project_root / ".simflow"), "computation", dry_run=False)
        input_manifest = result["manifests"]["input_generation"]
        compute_manifest = result["manifests"]["compute"]

        assert result["status"] == "completed"
        assert input_manifest["software"] == "lammps"
        assert input_manifest["actual_tool_used"]["support_level"] == "helper_supported"
        assert input_manifest["source"] == "user_provided_input_files"
        assert input_manifest["generated_files"] == [
            "inputs/lammps/in.lammps",
            "inputs/lammps/data.lammps",
        ]
        assert compute_manifest["software"] == "lammps"
        assert compute_manifest["actual_tool_used"]["support_level"] == "helper_supported"
        assert compute_manifest["recommended_command"] == "lmp -in in.lammps"
        assert compute_manifest["dry_run"] is True
        assert compute_manifest["real_submit"] is False


def test_execute_stage_generates_lammps_inputs_from_modeling_artifact():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        init_research(
            input_text="\n".join([
                "entry_stage: modeling",
                "goal: build LAMMPS input evidence",
                "material: Si",
                "software: lammps",
                "parameters: {\"structure_type\": \"diamond\", \"lattice_param\": 5.43, \"elements\": [\"Si\"], \"task\": \"minimize\", \"pair_style\": \"lj/cut\", \"pair_coeff\": \"* * 1.0 1.0\", \"force_field_source\": \"dimensionless LJ smoke fixture\"}",
            ]),
            output_dir=tmpdir,
        )
        modeling_result = execute_stage(str(project_root / ".simflow"), "modeling", dry_run=False)

        result = execute_stage(str(project_root / ".simflow"), "computation", dry_run=False)
        input_manifest = result["manifests"]["input_generation"]

        assert modeling_result["status"] == "completed"
        assert result["status"] == "completed"
        assert input_manifest["software"] == "lammps"
        assert input_manifest["actual_tool_used"]["support_level"] == "helper_supported"
        assert input_manifest["task"] == "minimize"
        assert input_manifest["force_field_provenance"]["redistributed_by_simflow"] is False
        assert ".simflow/artifacts/input_generation/in.lammps" in input_manifest["generated_files"]
        assert ".simflow/artifacts/input_generation/data.lammps" in input_manifest["generated_files"]
        assert (project_root / ".simflow" / "artifacts" / "input_generation" / "lammps_input_manifest.json").is_file()


def test_execute_stage_returns_capability_warning_for_tracked_only_input_generation():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        init_research(
            input_text="\n".join([
                "entry_stage: modeling",
                "goal: build GPUMD NEP workflow",
                "method: mlp_md",
                "material: Si",
                "software: gpumd",
                "toolchain: gpumd, nep",
                "parameters: {\"structure_type\": \"diamond\", \"lattice_param\": 5.43, \"elements\": [\"Si\"]}",
            ]),
            output_dir=tmpdir,
        )

        modeling = execute_stage(str(project_root / ".simflow"), "modeling", dry_run=False)
        result = execute_stage(str(project_root / ".simflow"), "computation", dry_run=False)
        stages_state = read_state(tmpdir, "stages.json")

        assert modeling["status"] == "completed"
        assert result["status"] == "capability_warning"
        assert result["warning"]["software"] == "gpumd"
        assert result["warning"]["support_level"] == "tracked_only"
        assert result["scripts"][0]["status"] == "warning"
        assert stages_state["computation"]["status"] == "waiting"


def test_execute_stage_returns_capability_warning_for_tracked_only_classical_md_tool():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        init_research(
            input_text="\n".join([
                "entry_stage: modeling",
                "goal: build classical MD workflow",
                "method: classical_md",
                "material: Si",
                "software: gromacs",
                "parameters: {\"structure_type\": \"diamond\", \"lattice_param\": 5.43, \"elements\": [\"Si\"]}",
            ]),
            output_dir=tmpdir,
        )

        modeling = execute_stage(str(project_root / ".simflow"), "modeling", dry_run=False)
        result = execute_stage(str(project_root / ".simflow"), "computation", dry_run=False)
        stages_state = read_state(tmpdir, "stages.json")

        assert modeling["status"] == "completed"
        assert result["status"] == "capability_warning"
        assert result["warning"]["software"] == "gromacs"
        assert result["warning"]["support_level"] == "tracked_only"
        assert stages_state["computation"]["status"] == "waiting"


def test_execute_stage_returns_capability_warning_for_unknown_tool_without_admission_block():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        init_research(
            input_text="\n".join([
                "entry_stage: modeling",
                "goal: build custom MD workflow",
                "method: custom",
                "material: Si",
                "software: bespoke_md",
                "parameters: {\"structure_type\": \"diamond\", \"lattice_param\": 5.43, \"elements\": [\"Si\"]}",
            ]),
            output_dir=tmpdir,
        )

        modeling = execute_stage(str(project_root / ".simflow"), "modeling", dry_run=False)
        result = execute_stage(str(project_root / ".simflow"), "computation", dry_run=False)
        stages_state = read_state(tmpdir, "stages.json")
        checkpoints = read_state(tmpdir, "checkpoints.json")

        assert modeling["status"] == "completed"
        assert result["status"] == "capability_warning"
        assert result["warning"]["software"] == "bespoke_md"
        assert result["warning"]["support_level"] == "unknown"
        assert result["warning"]["message"].startswith("No built-in SimFlow helper is available")
        assert stages_state["computation"]["status"] == "waiting"
        assert stages_state["computation"].get("checkpoint_id") is None
        assert checkpoints == []



def test_execute_stage_execute_runs_analysis_and_visualization_without_outputs():
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
        pipeline_result = run_pipeline(str(project_root / ".simflow"), target_stage="computation", dry_run=False)

        analysis_result = execute_stage(str(project_root / ".simflow"), "analysis_visualization", dry_run=False)
        artifacts = list_artifacts(stage="analysis_visualization", project_root=tmpdir)
        artifact_names = {artifact["name"] for artifact in artifacts}

        assert pipeline_result["status"] == "success"
        assert analysis_result["status"] == "completed"
        assert analysis_result["manifest"]["status"] == "waiting_for_outputs"
        assert analysis_result["manifest"]["visual_qa"]["status"] == "skipped"
        assert {"analysis_report.json", "analysis_report.md", "figures_manifest.json"} == artifact_names


def test_execute_stage_allows_direct_analysis_entry_with_user_outputs():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        outputs_dir = project_root / "outputs"
        outputs_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(VASP_RUN_XML, outputs_dir / "vasprun.xml")
        init_research(
            input_text="\n".join([
                "entry_stage: analysis_visualization",
                "goal: analyze existing VASP output",
                "material: Si",
                "software: vasp",
                "parameters: {\"output_files\": [\"outputs/vasprun.xml\"]}",
            ]),
            output_dir=tmpdir,
        )

        result = execute_stage(str(project_root / ".simflow"), "analysis_visualization", dry_run=False)
        artifacts = list_artifacts(stage="analysis_visualization", project_root=tmpdir)
        analysis_manifest = result["manifests"]["analysis"]

        assert result["status"] == "completed"
        assert analysis_manifest["compute_context"] == "user_provided_outputs"
        assert analysis_manifest["source_files"] == ["outputs/vasprun.xml"]
        assert analysis_manifest["analysis_provenance"]["compute_plan_artifact_id"] is None
        assert any(artifact["type"] == "user_provided_compute_output" for artifact in artifacts)
        assert {"analysis_report.json", "analysis_report.md", "figures_manifest.json"}.issubset(
            {artifact["name"] for artifact in artifacts}
        )
        assert (project_root / ".simflow" / "reports" / "analysis" / "analysis_report.json").is_file()
        assert (project_root / ".simflow" / "reports" / "visualization" / "figures_manifest.json").is_file()


def test_execute_stage_allows_direct_lammps_analysis_entry_with_user_log():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        outputs_dir = project_root / "outputs"
        outputs_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / "tests" / "fixtures" / "lammps_log.lammps", outputs_dir / "log.lammps")
        init_research(
            input_text="\n".join([
                "entry_stage: analysis_visualization",
                "goal: analyze existing LAMMPS log",
                "material: Si",
                "software: lammps",
                "parameters: {\"output_files\": [\"outputs/log.lammps\"]}",
            ]),
            output_dir=tmpdir,
        )

        result = execute_stage(str(project_root / ".simflow"), "analysis_visualization", dry_run=False)
        analysis_manifest = result["manifests"]["analysis"]
        visualization_manifest = result["manifests"]["visualization"]
        artifacts = list_artifacts(stage="analysis_visualization", project_root=tmpdir)

        assert result["status"] == "completed"
        assert analysis_manifest["software"] == "lammps"
        assert analysis_manifest["status"] == "completed"
        assert analysis_manifest["source_files"] == ["outputs/log.lammps"]
        assert analysis_manifest["final_energy"] == -37.65467
        assert analysis_manifest["temperature"] == 2567.89012
        assert analysis_manifest["trajectory_steps"] == 1000
        if importlib.util.find_spec("matplotlib") is None:
            assert visualization_manifest["status"] == "skipped_optional_dependency"
        else:
            assert visualization_manifest["status"] == "completed"
            assert visualization_manifest["figures"][0]["source_data"] == "outputs/log.lammps"
            assert (project_root / ".simflow" / "artifacts" / "visualization" / "energy_convergence.png").is_file()
        assert any(artifact["type"] == "user_provided_compute_output" for artifact in artifacts)



def test_execute_stage_execute_runs_analysis_and_visualization_with_vasp_outputs():
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
        pipeline_result = run_pipeline(str(project_root / ".simflow"), target_stage="computation", dry_run=False)
        compute_dir = project_root / ".simflow" / "artifacts" / "compute"
        shutil.copy2(VASP_RUN_XML, compute_dir / "vasprun.xml")
        (compute_dir / "OSZICAR").write_text(
            " 1 F= -.100000 E0= -.100000 d E =0.000000\n 2 F= -.200000 E0= -.200000 d E =0.000000\n",
            encoding="utf-8",
        )

        analysis_result = execute_stage(str(project_root / ".simflow"), "analysis_visualization", dry_run=False)
        artifacts = list_artifacts(stage="analysis_visualization", project_root=tmpdir)
        artifact_names = {artifact["name"] for artifact in artifacts}

        assert pipeline_result["status"] == "success"
        assert analysis_result["status"] == "completed"
        assert analysis_result["manifests"]["analysis"]["status"] == "completed"
        assert analysis_result["manifests"]["analysis"]["source_files"]
        assert analysis_result["manifests"]["analysis"]["analysis_provenance"]["input_artifact_ids"]
        assert analysis_result["manifests"]["visualization"]["figure_traceability"]["analysis_report_artifact_id"]
        assert "visual_qa" in analysis_result["manifests"]["visualization"]
        if importlib.util.find_spec("matplotlib") is None:
            assert analysis_result["manifests"]["visualization"]["status"] == "skipped_optional_dependency"
            assert analysis_result["manifests"]["visualization"]["visual_qa"]["status"] == "skipped_optional_dependency"
            assert {"analysis_report.json", "analysis_report.md", "figures_manifest.json"} == artifact_names
        else:
            assert analysis_result["manifests"]["visualization"]["status"] == "completed"
            assert {
                "analysis_report.json",
                "analysis_report.md",
                "figures_manifest.json",
                "energy_convergence_visual_qa.json",
                "energy_convergence.png",
            } == artifact_names
            assert (project_root / ".simflow" / "artifacts" / "visualization" / "energy_convergence.png").is_file()
            assert analysis_result["manifests"]["visualization"]["figures"][0]["source_data"].endswith("OSZICAR")
            assert analysis_result["manifests"]["visualization"]["figures"][0]["visual_qa"]["audit_artifact_id"]



def test_execute_stage_execute_runs_writing_runner_and_registers_artifacts():
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

        result = execute_stage(str(project_root / ".simflow"), "writing", dry_run=False)
        workflow = read_state(tmpdir, "workflow.json")
        stages_state = read_state(tmpdir, "stages.json")
        artifacts = list_artifacts(stage="writing", project_root=tmpdir)
        methods_path = project_root / ".simflow" / "reports" / "writing" / "methods.md"
        results_path = project_root / ".simflow" / "reports" / "writing" / "results.md"
        claim_map_path = project_root / ".simflow" / "reports" / "writing" / "claim_map.json"
        reproducibility_package_path = project_root / ".simflow" / "reports" / "reproducibility" / "reproducibility_package.md"
        final_handoff_markdown_path = project_root / ".simflow" / "reports" / "handoff" / "final_handoff.md"
        final_handoff_json_path = project_root / ".simflow" / "reports" / "handoff" / "final_handoff.json"

        assert precompute_result["status"] == "success"
        assert postcompute_result["status"] == "success"
        assert result["status"] == "completed"
        assert result["manifest"]["analysis_status"] == "waiting_for_outputs"
        assert result["manifest"]["visualization_status"] == "waiting_for_outputs"
        assert workflow["current_stage"] == "writing"
        assert workflow["status"] == "completed"
        assert stages_state["writing"]["status"] == "completed"
        assert len(stages_state["writing"]["inputs"]) == 7
        assert len(stages_state["writing"]["outputs"]) == 6
        assert {artifact["name"] for artifact in artifacts} == {
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
            for artifact in artifacts
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
        assert methods_path.is_file()
        assert results_path.is_file()
        assert claim_map_path.is_file()
        assert reproducibility_package_path.is_file()
        assert final_handoff_markdown_path.is_file()
        assert final_handoff_json_path.is_file()
        claim_map = json.loads(claim_map_path.read_text(encoding="utf-8"))
        assert {claim["claim_id"] for claim in claim_map["claims"]} == {
            "claim_001",
            "claim_002",
            "claim_003",
            "claim_004",
            "claim_005",
        }
        assert any(claim["speculative"] for claim in claim_map["claims"])
        assert "degraded or waiting" in results_path.read_text(encoding="utf-8")



def test_execute_stage_execute_generates_literature_artifacts():
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
                "pdfs: papers/surface.pdf",
                "bibtex: refs/references.bib",
                "dois: 10.1000/alpha",
            ]),
            output_dir=tmpdir,
        )

        result = execute_stage(str(project_root / ".simflow"), "literature_review", dry_run=False)
        workflow = read_state(tmpdir, "workflow.json")
        stages_state = read_state(tmpdir, "stages.json")
        artifacts = list_artifacts(stage="literature_review", project_root=tmpdir)

        assert result["status"] == "completed"
        assert workflow["current_stage"] == "literature_review"
        assert workflow["status"] == "in_progress"
        assert stages_state["literature_review"]["status"] == "completed"
        assert "literature" not in stages_state
        assert "review" not in stages_state
        assert set(stages_state["literature_review"]["outputs"]) == {
            artifact["artifact_id"] for artifact in artifacts
        }
        assert {
            "literature_matrix.json",
            "literature_matrix.csv",
            "search_log.json",
            "screening_record.json",
            "citation_map.json",
            "review_summary.md",
            "gap_analysis.md",
        }.issubset({artifact["name"] for artifact in artifacts})
        assert any(artifact["type"] == "paper_notes" for artifact in artifacts)
        assert (project_root / ".simflow" / "artifacts" / "literature" / "literature_matrix.json").is_file()
        assert result["artifacts"][0]["stage"] == "literature_review"
