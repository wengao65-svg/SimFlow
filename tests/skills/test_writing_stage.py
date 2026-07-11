#!/usr/bin/env python3
"""Tests for canonical writing stage runner behavior."""

import sys
import tempfile
import json
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "skills" / "simflow-writing" / "scripts"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(ROOT))

from runtime.simflow_core.artifacts import list_artifacts
from runtime.simflow_core.state import init_workflow
from run_writing_stage import _build_claim_map, _degraded_evidence_states, run_writing_stage
from runtime.simflow_helpers.stages.pipeline import run_pipeline
from runtime.simflow_helpers.project.intake import init_research

pytestmark = pytest.mark.filterwarnings(
    "ignore:Duplicate keys found.*ENCUT.*:pymatgen.io.vasp.inputs.BadIncarWarning"
)


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

        precompute_result = run_pipeline(str(project_root / ".simflow"), target_stage="computation", dry_run=False)
        postcompute_result = run_pipeline(str(project_root / ".simflow"), target_stage="analysis_visualization", dry_run=False)
        result = run_writing_stage(str(project_root / ".simflow"), dry_run=False)

        writing_artifacts = list_artifacts(stage="writing", project_root=tmpdir)
        methods_path = project_root / ".simflow" / "reports" / "writing" / "methods.md"
        results_path = project_root / ".simflow" / "reports" / "writing" / "results.md"
        claim_map_path = project_root / ".simflow" / "reports" / "writing" / "claim_map.json"
        reproducibility_package_path = project_root / ".simflow" / "reports" / "reproducibility" / "reproducibility_package.md"
        reproducibility_manifest_path = project_root / ".simflow" / "reports" / "reproducibility" / "reproducibility_manifest.json"
        final_handoff_markdown_path = project_root / ".simflow" / "reports" / "handoff" / "final_handoff.md"
        final_handoff_json_path = project_root / ".simflow" / "reports" / "handoff" / "final_handoff.json"
        verification_report_path = project_root / ".simflow" / "reports" / "verify" / "verification_report.json"

        assert precompute_result["status"] == "success"
        assert postcompute_result["status"] == "success"
        assert result["status"] == "success"
        assert result["manifest"]["analysis_status"] == "waiting_for_outputs"
        assert result["manifest"]["visualization_status"] == "waiting_for_outputs"
        assert result["manifest"]["verification_status"] in {"pass", "warning"}
        assert result["manifest"]["verification_report"] == ".simflow/reports/verify/verification_report.json"
        assert len(result["inputs"]) == 7
        assert {artifact["name"] for artifact in result["artifacts"]} == {
            "methods.md",
            "results.md",
            "claim_map.json",
            "reproducibility_package.md",
            "reproducibility_manifest.json",
            "final_handoff.md",
            "final_handoff.json",
            "verification_report.json",
        }
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
        assert len(result["artifacts"]) == 8
        assert {
            artifact["name"]
            for artifact in writing_artifacts
            if artifact["artifact_id"] in {output["artifact_id"] for output in result["artifacts"]}
        } == {
            "methods.md",
            "results.md",
            "claim_map.json",
            "reproducibility_package.md",
            "reproducibility_manifest.json",
            "final_handoff.md",
            "final_handoff.json",
            "verification_report.json",
        }
        assert [artifact["name"] for artifact in result["artifacts"]] == [
            "methods.md",
            "results.md",
            "claim_map.json",
            "reproducibility_package.md",
            "reproducibility_manifest.json",
            "final_handoff.md",
            "final_handoff.json",
            "verification_report.json",
        ]
        assert methods_path.is_file()
        assert results_path.is_file()
        assert claim_map_path.is_file()
        assert reproducibility_package_path.is_file()
        assert reproducibility_manifest_path.is_file()
        assert final_handoff_markdown_path.is_file()
        assert final_handoff_json_path.is_file()
        assert verification_report_path.is_file()

        methods_text = methods_path.read_text(encoding="utf-8")
        results_text = results_path.read_text(encoding="utf-8")
        claim_map = json.loads(claim_map_path.read_text(encoding="utf-8"))

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
        assert "## Degraded Evidence States" in results_text
        assert len(claim_map["claims"]) == 5
        assert claim_map["unresolved_degraded_state_count"] >= 3
        assert {item["area"] for item in claim_map["degraded_evidence_states"]} >= {
            "computation",
            "analysis",
            "visualization",
        }
        assert any(claim["status"] == "waiting_for_outputs" for claim in claim_map["claims"])
        assert any(claim["evidence_state"] == "dry_run_only" for claim in claim_map["claims"])
        assert "## Traceability / Source Artifact IDs" in results_text


def test_run_writing_stage_allows_direct_writing_entry_with_missing_upstream_artifacts():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        init_research(
            input_text="\n".join([
                "entry_stage: writing",
                "goal: draft an evidence-limited project note",
                "material: Si",
                "software: vasp",
            ]),
            output_dir=tmpdir,
        )

        result = run_writing_stage(str(project_root / ".simflow"), dry_run=False)
        claim_map_path = project_root / ".simflow" / "reports" / "writing" / "claim_map.json"
        methods_path = project_root / ".simflow" / "reports" / "writing" / "methods.md"
        claim_map = json.loads(claim_map_path.read_text(encoding="utf-8"))

        assert result["status"] == "success"
        assert result["inputs"] == []
        assert result["manifest"]["writing_input_status"] == "partial_missing_upstream_artifacts"
        assert result["manifest"]["analysis_status"] == "missing_evidence"
        assert claim_map["source_artifact_ids"] == []
        assert claim_map["unresolved_degraded_state_count"] >= 3
        assert any(claim["status"] == "missing_evidence" for claim in claim_map["claims"])
        assert any(claim["evidence_state"] == "missing_evidence" for claim in claim_map["claims"])
        assert any(claim["speculative"] is True for claim in claim_map["claims"])
        assert "Path: not_provided" in methods_path.read_text(encoding="utf-8")


def test_writing_claim_audit_classifies_tracked_only_and_conditional_evidence():
    compute_plan = {
        "real_submit": False,
        "actual_tool_used": {"software": "deepmd", "support_level": "tracked_only"},
        "status": "capability_warning",
    }
    analysis_report = {
        "status": "waiting",
        "actual_tool_used": {"software": "custom", "support_level": "tracked_only"},
        "missing_conditional_evidence": ["approval_record"],
        "blocked_claims": ["production MLP-MD readiness"],
    }
    figures_manifest = {
        "status": "skipped_optional_dependency",
        "figures": [],
        "skipped_reasons": ["matplotlib is not installed"],
    }

    states = _degraded_evidence_states(compute_plan, analysis_report, figures_manifest)
    state_pairs = {(state["area"], state["state"]) for state in states}

    assert ("computation", "dry_run_only") in state_pairs
    assert ("computation", "tracked_only_provenance") in state_pairs
    assert ("computation", "capability_warning_or_waiting") in state_pairs
    assert ("analysis", "conditional_evidence_missing") in state_pairs
    assert ("visualization", "skipped_optional_dependency") in state_pairs

    claim_map = _build_claim_map(
        contract={"research_goal": "test claim audit", "material": "Si"},
        required_artifacts={},
        structure_manifest={"source_mode": "not_provided"},
        compute_plan=compute_plan,
        analysis_report=analysis_report,
        figures_manifest=figures_manifest,
    )

    assert claim_map["blocked_claims"] == ["production MLP-MD readiness"]
    assert claim_map["unresolved_degraded_state_count"] >= 5


def test_writing_claim_audit_splits_scientific_ready_from_execution_gate():
    compute_plan = {
        "real_submit": False,
        "status": "completed",
    }
    analysis_report = {
        "status": "completed",
        "scientific_readiness": {"status": "ready"},
        "execution_gate": {
            "status": "approval_required",
            "gate": "production_md_readiness",
            "missing_roles": ["approval_record"],
            "real_submit_allowed": False,
        },
        "blocked_claims": ["real production MLP-MD execution"],
    }
    figures_manifest = {"status": "completed", "figures": []}

    states = _degraded_evidence_states(compute_plan, analysis_report, figures_manifest)
    state_pairs = {(state["area"], state["state"]) for state in states}
    blocked = {
        claim
        for state in states
        for claim in state.get("blocked_claims", [])
    }

    assert ("analysis", "execution_gate_approval_required") in state_pairs
    assert ("analysis", "scientific_readiness_blocked") not in state_pairs
    assert "real production MLP-MD execution" in blocked
    assert "production MLP-MD readiness" not in blocked


def test_writing_claim_audit_allows_readiness_approval_but_blocks_real_submit_claim():
    compute_plan = {
        "real_submit": False,
        "status": "completed",
    }
    analysis_report = {
        "status": "completed",
        "scientific_readiness": {"status": "ready"},
        "production_md_gate_approved": True,
        "execution_gate": {
            "status": "approved",
            "gate": "production_md_readiness",
            "gate_scope": "production_md_readiness_only",
            "production_md_gate_approved": True,
            "real_submit_allowed": False,
        },
    }
    figures_manifest = {"status": "completed", "figures": []}

    states = _degraded_evidence_states(compute_plan, analysis_report, figures_manifest)
    state_pairs = {(state["area"], state["state"]) for state in states}
    blocked = {
        claim
        for state in states
        for claim in state.get("blocked_claims", [])
    }

    assert ("analysis", "production_md_gate_approved") in state_pairs
    assert ("analysis", "execution_gate_approval_required") not in state_pairs
    assert "real production MLP-MD execution" in blocked
    assert "production MLP-MD readiness" not in blocked


def test_writing_claim_audit_ignores_legacy_mlp_real_submit_allowed():
    compute_plan = {
        "real_submit": False,
        "status": "completed",
    }
    analysis_report = {
        "status": "completed",
        "scientific_readiness": {"status": "ready"},
        "execution_gate": {
            "status": "approved",
            "gate": "production_md_readiness",
            "real_submit_allowed": True,
        },
        "real_submit_allowed": True,
    }
    figures_manifest = {"status": "completed", "figures": []}

    states = _degraded_evidence_states(compute_plan, analysis_report, figures_manifest)
    state_pairs = {(state["area"], state["state"]) for state in states}
    blocked = {
        claim
        for state in states
        for claim in state.get("blocked_claims", [])
    }

    assert ("analysis", "legacy_real_submit_allowed_ignored") in state_pairs
    assert "real production MLP-MD execution" in blocked
