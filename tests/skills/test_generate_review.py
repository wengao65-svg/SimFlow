#!/usr/bin/env python3
"""Tests for review summary and gap analysis generation."""

import json
import sys
import tempfile
from pathlib import Path

LITERATURE_DIR = Path(__file__).resolve().parents[2] / "skills" / "simflow-literature" / "scripts"
REVIEW_DIR = Path(__file__).resolve().parents[2] / "skills" / "simflow-review" / "scripts"
INTAKE_DIR = Path(__file__).resolve().parents[2] / "skills" / "simflow-intake" / "scripts"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(LITERATURE_DIR))
sys.path.insert(0, str(REVIEW_DIR))
sys.path.insert(0, str(INTAKE_DIR))
sys.path.insert(0, str(ROOT))

from runtime.lib.artifact import list_artifacts
from generate_literature_matrix import generate_literature_matrix
from generate_review import generate_review
from init_research import init_research



def test_generate_review_writes_markdown_and_registry_entries():
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
                "note: Focus on dimer buckling evidence",
            ]),
            output_dir=tmpdir,
        )
        generate_literature_matrix(str(project_root / ".simflow"))

        result = generate_review(str(project_root / ".simflow"))
        summary_path = project_root / ".simflow" / "reports" / "review" / "review_summary.md"
        gap_path = project_root / ".simflow" / "reports" / "review" / "gap_analysis.md"
        summary = summary_path.read_text(encoding="utf-8")
        gap_analysis = gap_path.read_text(encoding="utf-8")
        review_artifacts = list_artifacts(stage="review", project_root=tmpdir)
        literature_artifacts = list_artifacts(stage="literature", project_root=tmpdir)

        assert result["status"] == "success"
        assert summary_path.is_file()
        assert gap_path.is_file()
        assert "# Review Summary" in summary
        assert "Sources reviewed: 4" in summary
        assert "Focus on dimer buckling evidence" in summary
        assert "# Gap Analysis" in gap_analysis
        assert "Follow up on manual note: Focus on dimer buckling evidence" in gap_analysis
        assert len(review_artifacts) == 2
        assert review_artifacts[0]["name"] == "review_summary.md"
        assert review_artifacts[0]["path"] == ".simflow/reports/review/review_summary.md"
        assert review_artifacts[1]["name"] == "gap_analysis.md"
        assert review_artifacts[0]["lineage"]["parent_artifacts"] == [literature_artifacts[0]["artifact_id"]]
        assert review_artifacts[1]["lineage"]["parent_artifacts"] == [literature_artifacts[0]["artifact_id"]]



def test_generate_review_requires_registered_literature_matrix_artifact():
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
        literature_dir = project_root / ".simflow" / "artifacts" / "literature"
        literature_dir.mkdir(parents=True, exist_ok=True)
        (literature_dir / "literature_matrix.json").write_text(
            json.dumps({"row_count": 1, "rows": []}, indent=2),
            encoding="utf-8",
        )

        result = generate_review(str(project_root / ".simflow"))

        assert result["status"] == "error"
        assert result["message"] == "No literature matrix artifact found"



def test_generate_review_errors_without_workflow_state():
    with tempfile.TemporaryDirectory() as tmpdir:
        result = generate_review(str(Path(tmpdir) / ".simflow"))

        assert result["status"] == "error"
        assert result["message"] == "No workflow state found"
