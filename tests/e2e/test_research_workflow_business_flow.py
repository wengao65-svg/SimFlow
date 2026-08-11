#!/usr/bin/env python3
"""End-to-end business flow test: user text -> literature -> writing.

Asserts the full canonical chain produces traceable evidence at every stage,
using safe dry-run-only computation with no restricted or proprietary artifacts.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from runtime.simflow_core.artifacts import list_artifacts
from runtime.simflow_core.gates import check_gate
from runtime.simflow_core.state import read_state


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "runtime" / "simflow_helpers" / "legacy_workflow" / "run_research_workflow.py"


def _research_text() -> str:
    return "\n".join([
        "goal: prepare a traceable Si workflow",
        "material: Si diamond",
        "software: vasp",
        "method: dft",
        'parameters: {"encut": 520, "kppa": 100, "structure_type": "diamond", "lattice_param": 5.43, "elements": ["Si"]}',
        "note: Use dry-run computation evidence and do not submit real jobs.",
    ])


def test_research_workflow_business_flow_produces_full_evidence_chain(tmp_path):
    result = subprocess.run(
        [
            "python",
            str(SCRIPT),
            "--project-root",
            str(tmp_path),
            "--text",
            _research_text(),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    summary = json.loads(result.stdout)

    assert summary["status"] == "success"
    assert summary["current_stage"] == "writing"
    assert summary["workflow_status"] == "completed"
    assert summary["stages_executed"] == 6
    assert summary["completed_stages"] == [
        "literature_review",
        "proposal",
        "modeling",
        "computation",
        "analysis_visualization",
        "writing",
    ]

    artifacts = list_artifacts(project_root=str(tmp_path))
    artifact_names = {a["name"] for a in artifacts}
    artifact_types = {a["type"] for a in artifacts}

    lit_dir = tmp_path / ".simflow" / "artifacts" / "literature"
    search_log = json.loads((lit_dir / "search_log.json").read_text(encoding="utf-8"))
    citation_map = json.loads((lit_dir / "citation_map.json").read_text(encoding="utf-8"))

    assert search_log["source_policy"] == "user_provided_or_agent_selected_sources"
    assert search_log["provider_constraints"] == "none_fixed_by_simflow"
    assert search_log["sources"]
    for source in search_log["sources"]:
        assert source["access_status"]
    assert citation_map["entries"]
    for entry in citation_map["entries"]:
        assert entry["access_status"]
        assert entry["verification_status"]
    assert {"search_log", "citation_map", "paper_notes"}.issubset(artifact_types)
    assert len(list((lit_dir / "paper_notes").glob("*.md"))) >= 1

    proposal_contract = json.loads(
        (tmp_path / ".simflow" / "plans" / "proposal_contract.json").read_text(encoding="utf-8")
    )
    assert proposal_contract["calculation_plan"]["dry_run_first"] is True
    assert proposal_contract["resource_assumptions"]["real_submit"] is False
    assert proposal_contract["decision_criteria"]
    assert proposal_contract["risk_register"]
    assert proposal_contract["source_artifact_ids"]
    assert (tmp_path / ".simflow" / "plans" / "protocol_contract.json").is_file()
    assert "proposal_contract.json" in artifact_names
    assert "protocol_contract.json" in artifact_names

    assert (tmp_path / ".simflow" / "reports" / "modeling" / "structure_manifest.json").is_file()
    assert "structure_manifest.json" in artifact_names

    compute_dir = tmp_path / ".simflow" / "artifacts" / "compute"
    assert (compute_dir / "dry_run_report.json").is_file()
    assert (compute_dir / "input_validation.json").is_file()
    assert (tmp_path / ".simflow" / "artifacts" / "security" / "credential_scan.json").is_file()
    assert (tmp_path / ".simflow" / "reports" / "compute" / "submit_readiness_summary.md").is_file()

    compute_plan = json.loads(
        (tmp_path / ".simflow" / "reports" / "compute" / "compute_plan.json").read_text(encoding="utf-8")
    )
    assert compute_plan["user_submit_readiness"]["real_submit_allowed"] is False
    assert compute_plan["user_submit_readiness"]["approval_required"] is True
    assert "submit_readiness_summary.md" in artifact_names

    gate = check_gate("hpc_submit", {"project_root": str(tmp_path)})
    assert gate["status"] == "block"

    analysis_report = json.loads(
        (tmp_path / ".simflow" / "reports" / "analysis" / "analysis_report.json").read_text(encoding="utf-8")
    )
    assert analysis_report["analysis_provenance"]["input_artifact_ids"]
    assert analysis_report["analysis_provenance"]["environment"]["python"]
    assert "analysis_report.json" in artifact_names

    figures_manifest = json.loads(
        (tmp_path / ".simflow" / "reports" / "visualization" / "figures_manifest.json").read_text(encoding="utf-8")
    )
    assert figures_manifest["figure_traceability"]["analysis_report_artifact_id"]
    assert figures_manifest["environment"]["python"]
    assert "figures_manifest.json" in artifact_names

    claim_map = json.loads(
        (tmp_path / ".simflow" / "reports" / "writing" / "claim_map.json").read_text(encoding="utf-8")
    )
    assert claim_map["claims"]
    assert any(claim["speculative"] for claim in claim_map["claims"])
    assert "claim_map.json" in artifact_names

    assert (tmp_path / ".simflow" / "reports" / "writing" / "methods.md").is_file()
    assert (tmp_path / ".simflow" / "reports" / "writing" / "results.md").is_file()
    assert (tmp_path / ".simflow" / "reports" / "reproducibility" / "reproducibility_package.md").is_file()
    assert (tmp_path / ".simflow" / "reports" / "handoff" / "final_handoff.md").is_file()
    assert (tmp_path / ".simflow" / "reports" / "handoff" / "final_handoff.json").is_file()
    assert (tmp_path / ".simflow" / "reports" / "verify" / "verification_report.json").is_file()

    verification_report = json.loads(
        (tmp_path / ".simflow" / "reports" / "verify" / "verification_report.json").read_text(encoding="utf-8")
    )
    check_names = {check["name"] for check in verification_report["checks"]}
    assert "claim_traceability" in check_names
    claim_check = next(check for check in verification_report["checks"] if check["name"] == "claim_traceability")
    assert claim_check["status"] in {"pass", "warning"}

    assert summary["artifact_summary"]["total"] >= 30
    assert summary["checkpoint_summary"]["count"] >= 2
    assert summary["checkpoint_summary"]["latest"]
    assert summary["next_actions"]
    assert summary["lineage_summary"]

    jobs = read_state(project_root=str(tmp_path), state_file="jobs.json")
    assert jobs == []
