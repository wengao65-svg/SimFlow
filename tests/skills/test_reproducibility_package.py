#!/usr/bin/env python3
"""Tests for reproducibility package builder behavior."""

import json
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

from build_reproducibility_package import build_reproducibility_package
from init_research import init_research
from run_pipeline import run_pipeline
from runtime.lib.artifact import list_artifacts, register_artifact


def test_build_reproducibility_package_generates_outputs_and_registers_artifacts():
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

        pipeline_result = run_pipeline(str(project_root / ".simflow"), target_stage="visualization", dry_run=False)
        methods_path = project_root / ".simflow" / "reports" / "writing" / "methods.md"
        results_path = project_root / ".simflow" / "reports" / "writing" / "results.md"
        methods_path.parent.mkdir(parents=True, exist_ok=True)
        methods_path.write_text("# Methods\n", encoding="utf-8")
        results_path.write_text("# Results\n", encoding="utf-8")

        methods_artifact = register_artifact(
            "methods.md",
            "methods",
            "writing",
            project_root=tmpdir,
            path=".simflow/reports/writing/methods.md",
            parent_artifacts=[artifact["artifact_id"] for artifact in list_artifacts(project_root=tmpdir) if artifact["stage"] != "writing"],
            software="vasp",
        )
        results_artifact = register_artifact(
            "results.md",
            "results",
            "writing",
            project_root=tmpdir,
            path=".simflow/reports/writing/results.md",
            parent_artifacts=[methods_artifact["artifact_id"]],
            software="vasp",
        )

        result = build_reproducibility_package(
            str(project_root / ".simflow"),
            parent_artifact_ids=[methods_artifact["artifact_id"], results_artifact["artifact_id"]],
            software="vasp",
            write_manifest_json=True,
        )

        writing_artifacts = list_artifacts(stage="writing", project_root=tmpdir)
        package_path = project_root / ".simflow" / "reports" / "reproducibility" / "reproducibility_package.md"
        manifest_path = project_root / ".simflow" / "reports" / "reproducibility" / "reproducibility_manifest.json"

        assert pipeline_result["status"] == "success"
        assert result["status"] == "success"
        assert package_path.is_file()
        assert manifest_path.is_file()
        assert {artifact["name"] for artifact in result["artifacts"]} == {"reproducibility_package.md", "reproducibility_manifest.json"}
        assert {artifact["name"] for artifact in writing_artifacts} >= {
            "methods.md",
            "results.md",
            "reproducibility_package.md",
            "reproducibility_manifest.json",
        }

        content = package_path.read_text(encoding="utf-8")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        assert "# Reproducibility Package" in content
        assert "## Artifact Index" in content
        assert "## Execution Truth" in content
        assert manifest["execution_truth"]["dry_run"] is True
        assert manifest["execution_truth"]["real_submit"] is False
        assert manifest["writing_artifact_references"]["methods"]["name"] == "methods.md"
        assert manifest["writing_artifact_references"]["results"]["name"] == "results.md"
