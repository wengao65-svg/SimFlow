#!/usr/bin/env python3
"""Tests for canonical writing stage runner behavior."""

import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "skills" / "simflow-writing" / "scripts"
PIPELINE_DIR = Path(__file__).resolve().parents[2] / "skills" / "simflow-pipeline" / "scripts"
INTAKE_DIR = Path(__file__).resolve().parents[2] / "skills" / "simflow-intake" / "scripts"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(PIPELINE_DIR))
sys.path.insert(0, str(INTAKE_DIR))
sys.path.insert(0, str(ROOT))

from runtime.lib.artifact import list_artifacts
from runtime.lib.state import init_workflow
from run_writing_stage import run_writing_stage
from run_pipeline import run_pipeline
from init_research import init_research


def test_run_writing_stage_requires_canonical_upstream_artifacts():
    with tempfile.TemporaryDirectory() as tmpdir:
        init_workflow("dft", "literature", tmpdir)

        result = run_writing_stage(str(Path(tmpdir) / ".simflow"), dry_run=False)

        assert result["status"] == "error"
        assert "Missing proposal artifacts" in result["message"]


def test_run_writing_stage_generates_methods_and_results_from_waiting_outputs():
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
        result = run_writing_stage(str(project_root / ".simflow"), dry_run=False)

        writing_artifacts = list_artifacts(stage="writing", project_root=tmpdir)
        methods_path = project_root / ".simflow" / "reports" / "writing" / "methods.md"
        results_path = project_root / ".simflow" / "reports" / "writing" / "results.md"

        assert precompute_result["status"] == "success"
        assert postcompute_result["status"] == "success"
        assert result["status"] == "success"
        assert result["manifest"]["analysis_status"] == "waiting_for_outputs"
        assert result["manifest"]["visualization_status"] == "waiting_for_outputs"
        assert len(result["inputs"]) == 7
        assert {artifact["name"] for artifact in writing_artifacts} == {"methods.md", "results.md"}
        assert methods_path.is_file()
        assert results_path.is_file()

        methods_text = methods_path.read_text(encoding="utf-8")
        results_text = results_path.read_text(encoding="utf-8")

        assert "## Research Goal" in methods_text
        assert "## System and Material" in methods_text
        assert "## Software" in methods_text
        assert "## Modeling Summary" in methods_text
        assert "## Compute Configuration" in methods_text
        assert "## Parameter Table Summary" in methods_text
        assert "## Source Artifact IDs" in methods_text

        assert "## Analysis Summary" in results_text
        assert "## Visualization Summary" in results_text
        assert "Status: waiting_for_outputs" in results_text
        assert "degraded or waiting" in results_text
        assert "## Traceability / Source Artifact IDs" in results_text
