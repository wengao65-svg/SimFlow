#!/usr/bin/env python3
"""Tests for literature matrix generation and artifact registration."""

import csv
import json
import sys
import tempfile
from pathlib import Path

LITERATURE_DIR = Path(__file__).resolve().parents[2] / "skills" / "simflow-literature" / "scripts"
INTAKE_DIR = Path(__file__).resolve().parents[2] / "skills" / "simflow-intake" / "scripts"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(LITERATURE_DIR))
sys.path.insert(0, str(INTAKE_DIR))
sys.path.insert(0, str(ROOT))

from runtime.lib.artifact import list_artifacts
from runtime.lib.state import read_state
from generate_literature_matrix import generate_literature_matrix
from init_research import init_research



def test_generate_literature_matrix_writes_json_csv_and_registry_entries():
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

        result = generate_literature_matrix(str(project_root / ".simflow"))
        json_path = project_root / ".simflow" / "artifacts" / "literature" / "literature_matrix.json"
        csv_path = project_root / ".simflow" / "artifacts" / "literature" / "literature_matrix.csv"
        artifacts = list_artifacts(project_root=tmpdir, stage="literature")
        matrix = json.loads(json_path.read_text(encoding="utf-8"))

        assert result["status"] == "success"
        assert json_path.is_file()
        assert csv_path.is_file()
        assert matrix["source_counts"] == {"pdf": 1, "bibtex": 1, "doi": 1, "note": 1}
        assert matrix["row_count"] == 4
        assert matrix["rows"][0]["source_type"] == "pdf"
        assert matrix["rows"][1]["locator"] == "refs/references.bib"
        assert matrix["rows"][2]["locator"] == "10.1000/alpha"
        assert matrix["rows"][3]["notes"] == "Focus on dimer buckling evidence"
        assert len(artifacts) == 2
        assert artifacts[0]["name"] == "literature_matrix.json"
        assert artifacts[0]["path"] == ".simflow/artifacts/literature/literature_matrix.json"
        assert artifacts[1]["name"] == "literature_matrix.csv"
        assert artifacts[1]["lineage"]["parent_artifacts"] == [artifacts[0]["artifact_id"]]

        with csv_path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        assert len(rows) == 4
        assert rows[0]["source_type"] == "pdf"
        assert rows[3]["notes"] == "Focus on dimer buckling evidence"



def test_generate_literature_matrix_enriches_doi_rows_when_backend_requested():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        pdf_path = project_root / "papers" / "surface.pdf"
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_path.write_text("pdf placeholder", encoding="utf-8")

        init_research(
            input_text="\n".join([
                "goal: study Si bulk properties",
                "material: Si",
                "pdfs: papers/surface.pdf",
                "dois: 10.1103/PhysRevB.97.165202",
            ]),
            output_dir=tmpdir,
        )

        result = generate_literature_matrix(str(project_root / ".simflow"), enrich_backend="mock")
        matrix = result["matrix"]
        doi_row = next(row for row in matrix["rows"] if row["source_type"] == "doi")

        assert result["status"] == "success"
        assert matrix["enrichment"] == {
            "backend": "mock",
            "enabled": True,
            "attempted": 1,
            "enriched": 1,
            "failed": 0,
            "errors": [],
        }
        assert doi_row["title"] == "First-principles study of silicon crystal structure"
        assert doi_row["journal"] == "Physical Review B"
        assert doi_row["year"] == 2018
        assert doi_row["enrichment_source"] == "mock"



def test_generate_literature_matrix_ignores_legacy_metadata_file():
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
        legacy_metadata = project_root / ".simflow" / "metadata.json"
        legacy_metadata.write_text(
            json.dumps({"research_sources": {"counts": {"pdf": 99, "bibtex": 0, "doi": 0, "note": 0}}}, indent=2),
            encoding="utf-8",
        )

        result = generate_literature_matrix(str(project_root / ".simflow"))
        matrix = result["matrix"]
        metadata = read_state(tmpdir, "metadata.json")

        assert result["status"] == "success"
        assert metadata["research_sources"]["counts"] == {"pdf": 1, "bibtex": 0, "doi": 0, "note": 0}
        assert matrix["source_counts"] == {"pdf": 1, "bibtex": 0, "doi": 0, "note": 0}
        assert matrix["row_count"] == 1



def test_generate_literature_matrix_degrades_when_enrichment_backend_is_unknown():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        pdf_path = project_root / "papers" / "surface.pdf"
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_path.write_text("pdf placeholder", encoding="utf-8")

        init_research(
            input_text="\n".join([
                "goal: study Si bulk properties",
                "material: Si",
                "pdfs: papers/surface.pdf",
                "dois: 10.1103/PhysRevB.97.165202",
            ]),
            output_dir=tmpdir,
        )

        result = generate_literature_matrix(str(project_root / ".simflow"), enrich_backend="unknown")
        matrix = result["matrix"]
        doi_row = next(row for row in matrix["rows"] if row["source_type"] == "doi")

        assert result["status"] == "success"
        assert matrix["enrichment"]["backend"] == "unknown"
        assert matrix["enrichment"]["enriched"] == 0
        assert matrix["enrichment"]["failed"] == 1
        assert matrix["enrichment"]["errors"] == ["Unknown backend: unknown"]
        assert doi_row["title"] == ""
        assert doi_row["enrichment_source"] == ""



def test_generate_literature_matrix_errors_without_workflow_state():
    with tempfile.TemporaryDirectory() as tmpdir:
        result = generate_literature_matrix(str(Path(tmpdir) / ".simflow"))

        assert result["status"] == "error"
        assert result["message"] == "No workflow state found"
