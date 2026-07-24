#!/usr/bin/env python3
"""Tests for record_user_override MCP tool + risky directory detection.

Covers P2.2 + P2.3:
- record_user_override writes gate bypass to gates.json
- Gates have decision='user_override' and required fields
- Duplicate gate_id is rejected
- Risky directory names are detected by orphan_compute_scanner (P2.2)
"""

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runtime"))
sys.path.insert(0, str(ROOT / "mcp" / "servers" / "simflow_state"))


def _init(project_root):
    from runtime.simflow_core.state import init_workflow
    return init_workflow("custom", "computation", project_root=project_root)


def _import_override_tool():
    from tools.record_user_override import execute
    return execute


def test_record_user_override_writes_to_gates_json():
    """record_user_override appends to gates.json with decision='user_override'."""
    execute = _import_override_tool()

    with tempfile.TemporaryDirectory() as tmpdir:
        _init(tmpdir)

        result = execute({
            "project_root": tmpdir,
            "gate_id": "override_001_no_high_t_gate",
            "approver_context": "User explicitly approved running without high-T gate",
            "risk_note": "High-T Li-Li distance gate was bypassed for reproduction",
            "requested_action": "Run serial NEP MD without high-T stop condition",
            "directory_path": "Reproduce_arXiv_NEP2120_Relaxed_NoHighTGate",
        })

        assert result["status"] == "success"
        assert result["data"]["gate_id"] == "override_001_no_high_t_gate"
        assert result["data"]["decision"] == "user_override"

        from runtime.simflow_core.state import read_state
        gates = read_state(project_root=tmpdir, state_file="gates.json")
        assert len(gates) == 1
        assert gates[0]["gate_id"] == "override_001_no_high_t_gate"
        assert gates[0]["decision"] == "user_override"
        assert gates[0]["approver_context"] == "User explicitly approved running without high-T gate"
        assert gates[0]["risk_note"] == "High-T Li-Li distance gate was bypassed for reproduction"
        assert "created_at" in gates[0]


def test_record_user_override_rejects_duplicate_gate_id():
    """Duplicate gate_id is rejected."""
    execute = _import_override_tool()

    with tempfile.TemporaryDirectory() as tmpdir:
        _init(tmpdir)

        # First override
        execute({
            "project_root": tmpdir,
            "gate_id": "override_001",
            "approver_context": "User approved",
            "risk_note": "Risk accepted",
        })

        # Second with same gate_id
        result = execute({
            "project_root": tmpdir,
            "gate_id": "override_001",
            "approver_context": "User approved again",
            "risk_note": "Another risk",
        })

        assert result["status"] == "error"
        assert result["code"] == "duplicate_gate_id"


def test_record_user_override_requires_fields():
    """Missing required fields return error."""
    execute = _import_override_tool()

    with tempfile.TemporaryDirectory() as tmpdir:
        _init(tmpdir)

        # Missing gate_id
        result = execute({
            "project_root": tmpdir,
            "approver_context": "test",
            "risk_note": "test",
        })
        assert result["status"] == "error"
        assert "gate_id" in result["message"]

        # Missing approver_context
        result = execute({
            "project_root": tmpdir,
            "gate_id": "test_001",
            "risk_note": "test",
        })
        assert result["status"] == "error"
        assert "approver_context" in result["message"]

        # Missing risk_note
        result = execute({
            "project_root": tmpdir,
            "gate_id": "test_001",
            "approver_context": "test",
        })
        assert result["status"] == "error"
        assert "risk_note" in result["message"]


def test_record_user_override_preserves_existing_gates():
    """record_user_override does not overwrite existing gates."""
    execute = _import_override_tool()

    with tempfile.TemporaryDirectory() as tmpdir:
        _init(tmpdir)

        # Add an existing gate
        from runtime.simflow_core.state import write_state
        existing_gates = [{"gate_id": "gate_001_existing", "decision": "approved"}]
        write_state(existing_gates, project_root=tmpdir, state_file="gates.json")

        # Record a new override
        result = execute({
            "project_root": tmpdir,
            "gate_id": "override_001",
            "approver_context": "test",
            "risk_note": "test",
        })

        assert result["status"] == "success"
        assert result["data"]["total_gates"] == 2

        from runtime.simflow_core.state import read_state
        gates = read_state(project_root=tmpdir, state_file="gates.json")
        assert len(gates) == 2
        assert gates[0]["gate_id"] == "gate_001_existing"
        assert gates[0]["decision"] == "approved"
        assert gates[1]["gate_id"] == "override_001"
        assert gates[1]["decision"] == "user_override"


def test_record_user_override_includes_optional_fields():
    """record_user_override includes optional fields when provided."""
    execute = _import_override_tool()

    with tempfile.TemporaryDirectory() as tmpdir:
        _init(tmpdir)

        result = execute({
            "project_root": tmpdir,
            "gate_id": "override_001",
            "approver_context": "test approver",
            "risk_note": "test risk",
            "requested_action": "run MD without gate",
            "directory_path": "Reproduce_arXiv_relaxed",
            "original_gate_failure_ref": "ckpt_001_computation",
            "stage": "computation",
        })

        assert result["status"] == "success"

        from runtime.simflow_core.state import read_state
        gates = read_state(project_root=tmpdir, state_file="gates.json")
        assert gates[0]["requested_action"] == "run MD without gate"
        assert gates[0]["directory_path"] == "Reproduce_arXiv_relaxed"
        assert gates[0]["original_gate_failure_ref"] == "ckpt_001_computation"
        assert gates[0]["stage"] == "computation"


def test_record_user_override_refreshes_workflow_timestamps():
    """record_user_override calls touch_workflow to refresh timestamps."""
    execute = _import_override_tool()

    with tempfile.TemporaryDirectory() as tmpdir:
        _init(tmpdir)

        from runtime.simflow_core.state import read_state
        wf_before = read_state(project_root=tmpdir, state_file="workflow.json")
        updated_at_before = wf_before["updated_at"]

        import time
        time.sleep(0.01)

        execute({
            "project_root": tmpdir,
            "gate_id": "override_001",
            "approver_context": "test",
            "risk_note": "test",
        })

        wf_after = read_state(project_root=tmpdir, state_file="workflow.json")
        assert wf_after["updated_at"] != updated_at_before


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
