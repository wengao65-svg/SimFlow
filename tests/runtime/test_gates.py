#!/usr/bin/env python3
"""Tests for verification gate engine."""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "runtime"))

from runtime.simflow_core.gates import (
    list_gates, load_gate, evaluate_conditions, check_gate,
    record_gate_decision, get_gate_decisions,
)


def _write_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_hpc_evidence(project_root: Path, *, include_credentials: bool = True):
    artifacts = project_root / ".simflow" / "artifacts"
    _write_json(artifacts / "compute" / "dry_run_report.json", {"status": "pass"})
    _write_json(artifacts / "compute" / "input_validation.json", {"missing_required_files": []})
    _write_json(artifacts / "compute" / "resource_estimate.json", {"status": "warning"})
    if include_credentials:
        _write_json(artifacts / "security" / "credential_scan.json", {"findings": []})


def test_list_gates():
    """All 9 gates should be listed."""
    gates = list_gates()
    assert len(gates) >= 9
    assert "hpc_submit" in gates
    assert "convergence_failure" in gates
    assert "resource_exceeds_budget" in gates
    print("  list_gates OK")


def test_load_gate():
    """Load hpc_submit gate and verify structure."""
    gate = load_gate("hpc_submit")
    assert gate["name"] == "hpc_submit"
    assert gate["type"] == "approval"
    assert gate["conditions"][0]["id"] == "dry_run_passed"
    assert gate["conditions"][0]["evidence"] == "compute/dry_run_report.json"
    assert gate["conditions"][-1]["id"] == "approval_present"
    assert "submit_job" in gate["actions_on_approve"]
    assert gate["auto_approve"] is False
    print("  load_gate OK")


def test_load_gate_not_found():
    """Loading nonexistent gate raises FileNotFoundError."""
    try:
        load_gate("nonexistent_gate")
        assert False, "Should have raised"
    except FileNotFoundError:
        pass
    print("  load_gate_not_found OK")


def test_evaluate_non_dict_conditions_are_blocked():
    """Non-evidence conditions never pass from boolean runtime context."""
    gate = {"conditions": ["convergence_check_performed"]}
    context = {"convergence_check_performed": True}
    result = evaluate_conditions(gate, context)
    assert result["all_met"] is False
    assert result["unmet"] == ["convergence_check_performed"]
    assert result["details"][0]["kind"] == "unsupported"
    assert result["details"][0]["error"] == "legacy_context_condition_not_supported"
    print("  evaluate_non_dict_conditions_are_blocked OK")


def test_evidence_conditions_all_met():
    """Non-submit approval gates use recorded evidence, not booleans."""
    gate = load_gate("convergence_failure")
    with tempfile.TemporaryDirectory() as tmpdir:
        _write_json(
            Path(tmpdir) / ".simflow" / "artifacts" / "compute" / "convergence_report.json",
            {"check_performed": True, "criteria_defined": True},
        )
        result = evaluate_conditions(gate, {"project_root": tmpdir})
    assert result["all_met"] is True
    assert len(result["unmet"]) == 0
    assert result["met"] == [
        "convergence_check_performed",
        "convergence_criteria_defined",
    ]
    assert all(detail["kind"] == "evidence" for detail in result["details"])
    print("  evidence_conditions_all_met OK")


def test_evidence_conditions_partial():
    """Partial evidence conditions return all_met=False with unmet list."""
    gate = load_gate("convergence_failure")
    with tempfile.TemporaryDirectory() as tmpdir:
        _write_json(
            Path(tmpdir) / ".simflow" / "artifacts" / "compute" / "convergence_report.json",
            {"check_performed": True, "criteria_defined": False},
        )
        result = evaluate_conditions(gate, {"project_root": tmpdir})
    assert result["all_met"] is False
    assert "convergence_criteria_defined" in result["unmet"]
    assert "convergence_check_performed" in result["met"]
    print("  evidence_conditions_partial OK")


def test_hpc_submit_boolean_only_context_blocks():
    """Evidence gates do not accept boolean-only runtime context."""
    gate = load_gate("hpc_submit")
    context = {
        "dry_run_passed": True,
        "input_files_complete": True,
        "resource_request_reasonable": True,
        "credentials_clean": True,
        "approval_present": True,
    }
    result = evaluate_conditions(gate, context)
    assert result["all_met"] is False
    assert len(result["unmet"]) == 5
    assert "dry_run_passed" in result["unmet"]
    assert all(detail["kind"] == "evidence" for detail in result["details"])
    assert all("actual" not in detail for detail in result["details"])
    print("  hpc_submit_boolean_only_context_blocks OK")


def test_hpc_submit_evidence_conditions_all_met():
    """HPC submit gate passes only with evidence artifacts and approval state."""
    gate = load_gate("hpc_submit")
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        _write_hpc_evidence(project_root)
        record_gate_decision(
            "hpc_submit", "approved", {"reason": "operator approved dry-run evidence"},
            project_root=tmpdir, agent="test_agent",
        )
        result = evaluate_conditions(gate, {"project_root": tmpdir})
    assert result["all_met"] is True
    assert len(result["unmet"]) == 0
    assert result["met"] == [
        "dry_run_passed",
        "input_files_complete",
        "resource_request_reasonable",
        "credentials_clean",
        "approval_present",
    ]
    assert all(detail["kind"] == "evidence" for detail in result["details"])
    print("  hpc_submit_evidence_conditions_all_met OK")


def test_hpc_submit_missing_evidence_blocks():
    """Missing required evidence keeps an approval gate blocked."""
    gate = load_gate("hpc_submit")
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        _write_hpc_evidence(project_root, include_credentials=False)
        record_gate_decision(
            "hpc_submit", "approved", {"reason": "credential scan missing on purpose"},
            project_root=tmpdir, agent="test_agent",
        )
        result = evaluate_conditions(gate, {"project_root": tmpdir})
    assert result["all_met"] is False
    assert "credentials_clean" in result["unmet"]
    credential_detail = next(d for d in result["details"] if d["id"] == "credentials_clean")
    assert credential_detail["error"].startswith("missing_evidence")
    print("  hpc_submit_missing_evidence_blocks OK")


def test_check_gate_pass():
    """check_gate returns status=pass when all conditions met."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _write_json(
            Path(tmpdir) / ".simflow" / "artifacts" / "compute" / "convergence_report.json",
            {"check_performed": True, "criteria_defined": True},
        )
        result = check_gate("convergence_failure", {"project_root": tmpdir})
    assert result["status"] == "pass"
    assert result["gate"] == "convergence_failure"
    assert "actions_on_approve" in result
    assert "accept_with_warning" in result["actions_on_approve"]
    print("  check_gate_pass OK")


def test_check_gate_block():
    """check_gate returns status=block when conditions unmet."""
    context = {
        "dry_run_passed": True,
        "input_files_complete": True,
        "resource_request_reasonable": True,
        "credentials_clean": True,
    }
    result = check_gate("hpc_submit", context)
    assert result["status"] == "block"
    assert "actions_on_reject" in result
    assert "suggest_fixes" in result["actions_on_reject"]
    assert "dry_run_passed" in result["conditions"]["unmet"]
    print("  check_gate_block OK")


def test_check_gate_with_thresholds():
    """resource_exceeds_budget gate includes thresholds in result."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _write_json(
            Path(tmpdir) / ".simflow" / "artifacts" / "proposal" / "resource_estimate.json",
            {"status": "exceeds_budget", "budget_threshold_defined": True},
        )
        result = check_gate("resource_exceeds_budget", {"project_root": tmpdir})
    assert result["status"] == "pass"
    assert "thresholds" in result
    assert result["thresholds"]["cpu_hours"] == 10000
    print("  check_gate_with_thresholds OK")


def test_record_and_get_decisions():
    """Record a gate decision and retrieve it."""
    with tempfile.TemporaryDirectory() as tmpdir:
        record = record_gate_decision(
            "hpc_submit", "approved",
            {"dry_run_passed": True},
            base_dir=tmpdir, agent="test_agent",
        )
        assert record["decision_id"].startswith("gate_decision_")
        decisions = get_gate_decisions("hpc_submit", base_dir=tmpdir)
        assert len(decisions) == 1
        assert decisions[0]["decision"] == "approved"
        assert decisions[0]["decision_id"] == record["decision_id"]
        assert decisions[0]["agent"] == "test_agent"
        assert decisions[0]["conditions"]["dry_run_passed"] is True
        state = json.loads((Path(tmpdir) / ".simflow" / "state" / "gates.json").read_text())
        assert state["hpc_submit"]["latest_decision"] == "approved"
        assert state["hpc_submit"]["latest_decision_id"] == record["decision_id"]
    print("  record_and_get_decisions OK")


def test_get_decisions_empty():
    """No decisions returns empty list."""
    with tempfile.TemporaryDirectory() as tmpdir:
        decisions = get_gate_decisions(base_dir=tmpdir)
        assert decisions == []
    print("  get_decisions_empty OK")


def test_all_gate_definitions_loadable():
    """All gate JSON files should load without error."""
    gates = list_gates()
    for name in gates:
        gate = load_gate(name)
        assert "name" in gate
        assert "conditions" in gate
        assert isinstance(gate["conditions"], list)
    print("  all_gate_definitions_loadable OK")


def test_hpc_submit_gate_realistic():
    """Simulate HPC submit gate from dry-run evidence through approval."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        _write_hpc_evidence(project_root)

        result = check_gate("hpc_submit", {"project_root": tmpdir})
        assert result["status"] == "block"
        assert "approval_present" in result["conditions"]["unmet"]

        record_gate_decision(
            "hpc_submit", "approved", {"reason": "reviewed evidence"},
            project_root=tmpdir, agent="test_agent",
        )
        result = check_gate("hpc_submit", {"project_root": tmpdir})
    assert result["status"] == "pass"
    assert result["conditions"]["all_met"] is True
    print("  hpc_submit_gate_realistic OK")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        print(f"  {t.__name__}...", end=" ")
        t()
        print("OK")
    print(f"\n  All {len(tests)} gate tests passed!")
