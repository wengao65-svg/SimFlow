#!/usr/bin/env python3
"""E2E coverage for Milestone D final handoff deliverables."""

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INTAKE_DIR = ROOT / "skills" / "simflow-intake" / "scripts"
PIPELINE_DIR = ROOT / "skills" / "simflow-pipeline" / "scripts"

sys.path.insert(0, str(INTAKE_DIR))
sys.path.insert(0, str(PIPELINE_DIR))
sys.path.insert(0, str(ROOT))

from runtime.lib.artifact import list_artifacts
from runtime.lib.state import read_state
from init_research import init_research
from run_pipeline import run_pipeline


def test_milestone_d_final_handoff_e2e():
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
        precompute = run_pipeline(str(simflow_dir), target_stage="compute", dry_run=False)
        postcompute = run_pipeline(str(simflow_dir), target_stage="visualization", dry_run=False)
        writing = run_pipeline(str(simflow_dir), target_stage="writing", dry_run=False)

        workflow = read_state(tmpdir, "workflow.json")
        writing_artifacts = list_artifacts(stage="writing", project_root=tmpdir)
        final_handoff_json_path = project_root / ".simflow" / "reports" / "handoff" / "final_handoff.json"
        final_handoff_md_path = project_root / ".simflow" / "reports" / "handoff" / "final_handoff.md"
        verification_report_path = project_root / ".simflow" / "reports" / "verify" / "verification_report.json"
        final_handoff = json.loads(final_handoff_json_path.read_text(encoding="utf-8"))
        verification_report = json.loads(verification_report_path.read_text(encoding="utf-8"))

        assert intake["status"] == "success"
        assert precompute["status"] == "success"
        assert postcompute["status"] == "success"
        assert writing["status"] == "success"
        assert workflow["status"] == "completed"
        assert workflow["current_stage"] == "writing"
        assert final_handoff_json_path.is_file()
        assert final_handoff_md_path.is_file()
        assert verification_report_path.is_file()
        assert final_handoff["workflow_metadata"]["workflow_type"] == "dft"
        assert final_handoff["current_stage"] == "writing"
        assert final_handoff["writing_outputs"]["methods"]["name"] == "methods.md"
        assert final_handoff["writing_outputs"]["results"]["name"] == "results.md"
        assert final_handoff["reproducibility_outputs"]["reproducibility_package"]["name"] == "reproducibility_package.md"
        assert final_handoff["compute_truth"]["dry_run"] is True
        assert final_handoff["compute_truth"]["real_submit"] is False
        assert final_handoff["compute_truth"]["approval_required_for_real_submit"] is True
        assert final_handoff["latest_checkpoint"] is not None
        assert verification_report["status"] in {"pass", "warning"}
        assert {check["name"] for check in verification_report["checks"]} == {
            "artifact_traceability",
            "required_writing_outputs",
            "reproducibility_manifest_present",
            "final_handoff_present",
            "compute_truth_declared",
            "no_real_submit_without_approval",
            "no_sensitive_paths",
            "checkpoint_summary_present",
        }
        assert set(artifact["name"] for artifact in writing_artifacts) >= {
            "methods.md",
            "results.md",
            "reproducibility_package.md",
            "final_handoff.md",
            "final_handoff.json",
            "verification_report.json",
        }
        assert tmpdir not in final_handoff_json_path.read_text(encoding="utf-8")
