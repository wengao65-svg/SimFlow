#!/usr/bin/env python3
"""E2E coverage for the minimum SimFlow backbone chain."""

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INTAKE_DIR = ROOT / "skills" / "simflow-intake" / "scripts"
PLAN_DIR = ROOT / "skills" / "simflow-plan" / "scripts"
PIPELINE_DIR = ROOT / "skills" / "simflow-pipeline" / "scripts"
HANDOFF_DIR = ROOT / "skills" / "simflow-handoff" / "scripts"

sys.path.insert(0, str(INTAKE_DIR))
sys.path.insert(0, str(PLAN_DIR))
sys.path.insert(0, str(PIPELINE_DIR))
sys.path.insert(0, str(HANDOFF_DIR))
sys.path.insert(0, str(ROOT))

from runtime.lib.artifact import list_artifacts
from runtime.lib.state import read_state
from init_research import init_research
from generate_plan import generate_plan
from run_pipeline import run_pipeline
from generate_handoff import generate_handoff


def test_backbone_workflow_e2e():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        simflow_dir = project_root / ".simflow"
        pdf_path = project_root / "papers" / "surface.pdf"
        bib_path = project_root / "refs" / "references.bib"
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        bib_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_path.write_text("pdf placeholder", encoding="utf-8")
        bib_path.write_text("@article{surface, title={Surface Study}}", encoding="utf-8")

        intake = init_research(
            input_text="\n".join([
                "goal: study Si surface",
                "material: Si(001)",
                "software: vasp",
                "parameters: {\"encut\": 520}",
                "pdfs: papers/surface.pdf",
                "bibtex: refs/references.bib",
                "dois: 10.1000/alpha",
                "note: Focus on dimer buckling evidence",
            ]),
            output_dir=tmpdir,
        )
        assert intake["status"] == "success"
        assert (simflow_dir / "state" / "workflow.json").is_file()
        assert (simflow_dir / "state" / "metadata.json").is_file()

        plan = generate_plan(str(simflow_dir))
        workflow_after_plan = read_state(tmpdir, "workflow.json")
        assert plan["status"] == "success"
        assert (simflow_dir / "plans" / "workflow_plan.json").is_file()
        assert workflow_after_plan["plan"] == "plans/workflow_plan.json"

        pipeline = run_pipeline(str(simflow_dir), target_stage="proposal", dry_run=False)
        workflow_after_pipeline = read_state(tmpdir, "workflow.json")
        stages_state = read_state(tmpdir, "stages.json")
        checkpoints = read_state(tmpdir, "checkpoints.json")
        artifacts = list_artifacts(project_root=tmpdir)
        artifact_names = [artifact["name"] for artifact in artifacts]
        assert pipeline["status"] == "success"
        assert [item["stage"] for item in pipeline["results"]] == ["literature", "review", "proposal"]
        assert stages_state["literature"]["status"] == "completed"
        assert stages_state["review"]["status"] == "completed"
        assert stages_state["proposal"]["status"] == "completed"
        assert workflow_after_pipeline["current_stage"] == "proposal"
        assert len(checkpoints) == 1
        assert checkpoints[0]["checkpoint_id"] == pipeline["checkpoint_id"]
        assert checkpoints[0]["stage_id"] == "proposal"
        assert artifact_names == [
            "literature_matrix.json",
            "literature_matrix.csv",
            "review_summary.md",
            "gap_analysis.md",
            "proposal.md",
            "parameter_table.csv",
            "research_questions.json",
        ]

        handoff = generate_handoff(str(simflow_dir))
        summary = handoff["handoff"]
        assert handoff["status"] == "success"
        assert summary["current_stage"] == "proposal"
        assert summary["completed_stages"] == ["literature", "review", "proposal"]
        assert summary["pending_stages"][0] == "modeling"
        assert summary["latest_checkpoint"]["checkpoint_id"] == pipeline["checkpoint_id"]
        assert summary["latest_checkpoint"]["stage_id"] == "proposal"
        assert summary["plan_reference"] == "plans/workflow_plan.json"
        assert summary["artifacts_count"] == 7
        assert sorted(summary["artifacts_by_stage"].keys()) == ["literature", "proposal", "review"]
        assert [artifact["name"] for artifact in summary["artifacts_by_stage"]["proposal"]] == ["proposal.md", "parameter_table.csv", "research_questions.json"]
