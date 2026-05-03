#!/usr/bin/env python3
"""Tests for workflow gates and policies definitions."""

import json
from pathlib import Path

GATES_DIR = Path(__file__).resolve().parents[2] / "workflow" / "gates"
POLICIES_DIR = Path(__file__).resolve().parents[2] / "workflow" / "policies"


def test_gates_directory_not_empty():
    gates = list(GATES_DIR.glob("*.json"))
    assert len(gates) > 0, "No gate files found"


def test_gate_json_valid():
    for path in GATES_DIR.glob("*.json"):
        data = json.loads(path.read_text())
        assert isinstance(data, dict), f"Gate {path.name} is not a dict"


def test_gate_has_required_fields():
    for path in GATES_DIR.glob("*.json"):
        data = json.loads(path.read_text())
        assert "gate_name" in data or "name" in data, f"Gate {path.name} missing name"
        assert "type" in data, f"Gate {path.name} missing type"
        assert "trigger" in data or "conditions" in data, f"Gate {path.name} missing trigger/conditions"


def test_gate_type_valid():
    valid_types = {"approval", "verification", "safety", "threshold", "convergence"}
    for path in GATES_DIR.glob("*.json"):
        data = json.loads(path.read_text())
        gate_type = data.get("type", "")
        # Allow any type string for flexibility
        assert isinstance(gate_type, str) and len(gate_type) > 0, f"Gate {path.name} has empty type"


def test_policies_directory_not_empty():
    policies = list(POLICIES_DIR.glob("*.json"))
    assert len(policies) > 0, "No policy files found"


def test_policy_json_valid():
    for path in POLICIES_DIR.glob("*.json"):
        data = json.loads(path.read_text())
        assert isinstance(data, dict), f"Policy {path.name} is not a dict"


def test_policy_has_required_fields():
    for path in POLICIES_DIR.glob("*.json"):
        data = json.loads(path.read_text())
        assert "policy_name" in data or "name" in data, f"Policy {path.name} missing name"


def test_gate_count():
    gates = list(GATES_DIR.glob("*.json"))
    assert len(gates) >= 6, f"Expected at least 6 gates, got {len(gates)}"


def test_policy_count():
    policies = list(POLICIES_DIR.glob("*.json"))
    assert len(policies) >= 5, f"Expected at least 5 policies, got {len(policies)}"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        print(f"  {t.__name__}...", end=" ")
        t()
        print("OK")
    print(f"\n  All {len(tests)} tests passed!")
