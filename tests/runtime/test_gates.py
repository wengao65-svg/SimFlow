#!/usr/bin/env python3
"""Tests for verification gate engine."""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "runtime"))

from lib.gates import (
    list_gates, load_gate, evaluate_conditions, check_gate,
    record_gate_decision, get_gate_decisions,
)


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
    assert "dry_run_passed" in gate["conditions"]
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


def test_evaluate_conditions_all_met():
    """All conditions met returns all_met=True."""
    gate = load_gate("hpc_submit")
    context = {
        "dry_run_passed": True,
        "input_files_complete": True,
        "resource_request_reasonable": True,
        "no_credential_in_files": True,
    }
    result = evaluate_conditions(gate, context)
    assert result["all_met"] is True
    assert len(result["unmet"]) == 0
    assert len(result["met"]) == 4
    print("  evaluate_conditions_all_met OK")


def test_evaluate_conditions_partial():
    """Partial conditions returns all_met=False with unmet list."""
    gate = load_gate("hpc_submit")
    context = {
        "dry_run_passed": True,
        "input_files_complete": False,
        "resource_request_reasonable": True,
        "no_credential_in_files": False,
    }
    result = evaluate_conditions(gate, context)
    assert result["all_met"] is False
    assert "input_files_complete" in result["unmet"]
    assert "no_credential_in_files" in result["unmet"]
    assert "dry_run_passed" in result["met"]
    print("  evaluate_conditions_partial OK")


def test_evaluate_conditions_empty_context():
    """Empty context means all conditions unmet."""
    gate = load_gate("hpc_submit")
    result = evaluate_conditions(gate, {})
    assert result["all_met"] is False
    assert len(result["unmet"]) == 4
    print("  evaluate_conditions_empty_context OK")


def test_check_gate_pass():
    """check_gate returns status=pass when all conditions met."""
    gate = load_gate("convergence_failure")
    context = {
        "convergence_check_performed": True,
        "convergence_criteria_defined": True,
    }
    result = check_gate("convergence_failure", context)
    assert result["status"] == "pass"
    assert result["gate"] == "convergence_failure"
    assert "actions_on_approve" in result
    assert "accept_with_warning" in result["actions_on_approve"]
    print("  check_gate_pass OK")


def test_check_gate_block():
    """check_gate returns status=block when conditions unmet."""
    gate = load_gate("hpc_submit")
    context = {
        "dry_run_passed": True,
        "input_files_complete": False,
    }
    result = check_gate("hpc_submit", context)
    assert result["status"] == "block"
    assert "actions_on_reject" in result
    assert "suggest_fixes" in result["actions_on_reject"]
    print("  check_gate_block OK")


def test_check_gate_with_thresholds():
    """resource_exceeds_budget gate includes thresholds in result."""
    context = {
        "resource_estimate_available": True,
        "budget_threshold_defined": True,
    }
    result = check_gate("resource_exceeds_budget", context)
    assert result["status"] == "pass"
    assert "thresholds" in result
    assert result["thresholds"]["cpu_hours"] == 10000
    print("  check_gate_with_thresholds OK")


def test_record_and_get_decisions():
    """Record a gate decision and retrieve it."""
    with tempfile.TemporaryDirectory() as tmpdir:
        record_gate_decision(
            "hpc_submit", "approved",
            {"dry_run_passed": True},
            base_dir=tmpdir, agent="test_agent",
        )
        decisions = get_gate_decisions("hpc_submit", base_dir=tmpdir)
        assert len(decisions) == 1
        assert decisions[0]["decision"] == "approved"
        assert decisions[0]["agent"] == "test_agent"
        assert decisions[0]["conditions"]["dry_run_passed"] is True
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
    """Simulate HPC submit gate: dry_run first, then full context."""
    # Before dry_run: missing conditions
    result = check_gate("hpc_submit", {})
    assert result["status"] == "block"
    assert len(result["conditions"]["unmet"]) == 4

    # After dry_run but missing credential check
    result = check_gate("hpc_submit", {
        "dry_run_passed": True,
        "input_files_complete": True,
        "resource_request_reasonable": True,
    })
    assert result["status"] == "block"
    assert "no_credential_in_files" in result["conditions"]["unmet"]

    # All checks pass
    result = check_gate("hpc_submit", {
        "dry_run_passed": True,
        "input_files_complete": True,
        "resource_request_reasonable": True,
        "no_credential_in_files": True,
    })
    assert result["status"] == "pass"
    print("  hpc_submit_gate_realistic OK")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        print(f"  {t.__name__}...", end=" ")
        t()
        print("OK")
    print(f"\n  All {len(tests)} gate tests passed!")
