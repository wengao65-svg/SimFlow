#!/usr/bin/env python3
"""Tests for proposal and parameter-table generation."""

import csv
import sys
import tempfile
from pathlib import Path

INTAKE_DIR = Path(__file__).resolve().parents[2] / "skills" / "simflow-intake" / "scripts"
LITERATURE_DIR = Path(__file__).resolve().parents[2] / "skills" / "simflow-literature" / "scripts"
REVIEW_DIR = Path(__file__).resolve().parents[2] / "skills" / "simflow-review" / "scripts"
PROPOSAL_DIR = Path(__file__).resolve().parents[2] / "skills" / "simflow-proposal" / "scripts"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(INTAKE_DIR))
sys.path.insert(0, str(LITERATURE_DIR))
sys.path.insert(0, str(REVIEW_DIR))
sys.path.insert(0, str(PROPOSAL_DIR))
sys.path.insert(0, str(ROOT))

from runtime.lib.artifact import list_artifacts
from generate_literature_matrix import generate_literature_matrix
from generate_proposal import generate_proposal
from generate_review import generate_review
from init_research import init_research



def test_generate_proposal_writes_markdown_csv_and_registry_entries():
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
                "parameters: {\"encut\": 520, \"kmesh\": \"4x4x1\"}",
                "pdfs: papers/surface.pdf",
                "bibtex: refs/references.bib",
                "dois: 10.1000/alpha",
                "note: Focus on dimer buckling evidence",
            ]),
            output_dir=tmpdir,
        )
        generate_literature_matrix(str(project_root / ".simflow"))
        generate_review(str(project_root / ".simflow"))

        result = generate_proposal(str(project_root / ".simflow"))
        proposal_path = project_root / ".simflow" / "plans" / "proposal.md"
        parameter_table_path = project_root / ".simflow" / "plans" / "parameter_table.csv"
        proposal_content = proposal_path.read_text(encoding="utf-8")
        proposal_artifacts = list_artifacts(stage="proposal", project_root=tmpdir)
        review_artifacts = list_artifacts(stage="review", project_root=tmpdir)

        assert result["status"] == "success"
        assert proposal_path.is_file()
        assert parameter_table_path.is_file()
        assert "# Proposal" in proposal_content
        assert "Goal: study Si surface reconstruction" in proposal_content
        assert "- encut: 520" in proposal_content
        assert "- kmesh: 4x4x1" in proposal_content
        assert "Focus on dimer buckling evidence" in proposal_content
        assert len(proposal_artifacts) == 2
        assert proposal_artifacts[0]["name"] == "proposal.md"
        assert proposal_artifacts[0]["path"] == ".simflow/plans/proposal.md"
        assert proposal_artifacts[0]["lineage"]["parent_artifacts"] == [artifact["artifact_id"] for artifact in review_artifacts]
        assert proposal_artifacts[1]["name"] == "parameter_table.csv"
        assert proposal_artifacts[1]["path"] == ".simflow/plans/parameter_table.csv"
        assert proposal_artifacts[1]["lineage"]["parent_artifacts"] == [proposal_artifacts[0]["artifact_id"]]

        with parameter_table_path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        assert rows[0]["parameter"] == "workflow_type"
        assert rows[1]["parameter"] == "software"
        assert rows[2]["parameter"] == "material"
        assert rows[3]["parameter"] == "encut"
        assert rows[3]["value"] == "520"
        assert rows[4]["parameter"] == "kmesh"
        assert rows[4]["value"] == "4x4x1"



def test_generate_proposal_requires_registered_review_artifacts():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        pdf_path = project_root / "papers" / "surface.pdf"
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_path.write_text("pdf placeholder", encoding="utf-8")

        init_research(
            input_text="\n".join([
                "goal: study Si surface reconstruction",
                "material: Si(001)",
                "pdfs: papers/surface.pdf",
            ]),
            output_dir=tmpdir,
        )
        generate_literature_matrix(str(project_root / ".simflow"))
        legacy_review = project_root / ".simflow" / "review_summary.md"
        legacy_review.write_text("legacy", encoding="utf-8")

        result = generate_proposal(str(project_root / ".simflow"))

        assert result["status"] == "error"
        assert result["message"] == "Missing review artifacts: review_summary.md, gap_analysis.md"



def test_generate_proposal_errors_without_workflow_state():
    with tempfile.TemporaryDirectory() as tmpdir:
        result = generate_proposal(str(Path(tmpdir) / ".simflow"))

        assert result["status"] == "error"
        assert result["message"] == "No workflow state found"
