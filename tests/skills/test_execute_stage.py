#!/usr/bin/env python3
"""Tests for simflow-stage canonical state behavior."""

import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "skills" / "simflow-stage" / "scripts"
PIPELINE_DIR = Path(__file__).resolve().parents[2] / "skills" / "simflow-pipeline" / "scripts"
INTAKE_DIR = Path(__file__).resolve().parents[2] / "skills" / "simflow-intake" / "scripts"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(PIPELINE_DIR))
sys.path.insert(0, str(INTAKE_DIR))
sys.path.insert(0, str(ROOT))

from runtime.lib.artifact import list_artifacts
from runtime.lib.state import init_workflow, read_state, write_state
from execute_stage import execute_stage
from init_research import init_research
from run_pipeline import run_pipeline


def _write_metadata(tmpdir: str, workflow_type: str = "dft"):
    state = read_state(tmpdir, "workflow.json")
    metadata = {
        "workflow_id": state["workflow_id"],
        "workflow_type": workflow_type,
        "entry_point": "literature" if workflow_type == "dft" else "proposal",
        "current_stage": "literature" if workflow_type == "dft" else "proposal",
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

        result = execute_stage(str(Path(tmpdir) / ".simflow"), "review", dry_run=True)
        stages_state = read_state(tmpdir, "stages.json")

        assert result["status"] == "dry_run_complete"
        assert result["stage"] == "review"
        assert stages_state["review"]["status"] == "pending"
        assert "legacy_stage" not in stages_state
        assert not (Path(tmpdir) / ".simflow" / "workflow_state.json").exists()


def test_execute_stage_rejects_stage_not_in_workflow_definition():
    with tempfile.TemporaryDirectory() as tmpdir:
        init_workflow("aimd", "proposal", tmpdir)
        _write_metadata(tmpdir, "aimd")

        result = execute_stage(str(Path(tmpdir) / ".simflow"), "literature", dry_run=True)
        stages_state = read_state(tmpdir, "stages.json")

        assert result["status"] == "error"
        assert result["message"] == "Unknown stage: literature"
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
        assert stages_state["modeling"]["inputs"] == [artifact["artifact_id"] for artifact in proposal_artifacts]
        assert len(stages_state["modeling"]["outputs"]) == 2
        assert result["scripts"][0]["status"] == "executed"
        assert {artifact["name"] for artifact in modeling_artifacts} == {"structure_manifest.json", "POSCAR_supercell"}
        assert (project_root / ".simflow" / "reports" / "modeling" / "structure_manifest.json").is_file()
        assert (project_root / ".simflow" / "artifacts" / "modeling" / "POSCAR_supercell").is_file()
        assert not (Path(tmpdir) / ".simflow" / "workflow_state.json").exists()
        assert not (Path(tmpdir) / ".simflow" / "metadata.json").exists()



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

        result = execute_stage(str(project_root / ".simflow"), "literature", dry_run=False)
        workflow = read_state(tmpdir, "workflow.json")
        stages_state = read_state(tmpdir, "stages.json")
        artifacts = list_artifacts(stage="literature", project_root=tmpdir)

        assert result["status"] == "completed"
        assert workflow["current_stage"] == "literature"
        assert workflow["status"] == "in_progress"
        assert stages_state["literature"]["status"] == "completed"
        assert len(stages_state["literature"]["outputs"]) == 2
        assert len(artifacts) == 2
        assert {artifact["name"] for artifact in artifacts} == {"literature_matrix.json", "literature_matrix.csv"}
        assert (project_root / ".simflow" / "artifacts" / "literature" / "literature_matrix.json").is_file()
        assert result["artifacts"][0]["stage"] == "literature"
