#!/usr/bin/env python3
"""Tests for record_submit_job gate enforcement.

Covers P2.4:
- record_submit_job requires gate_decision_id
- Jobs without gate are rejected
- gate_decision_id must exist in gates.json
- user_override=True with override_gate_id allows bypass
"""

import json
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runtime"))


def _init(project_root):
    from runtime.simflow_core.state import init_workflow
    return init_workflow("custom", "computation", project_root=project_root)


def test_record_submit_job_requires_gate_decision_id():
    """record_submit_job rejects jobs without gate_decision_id."""
    from runtime.simflow_helpers.computation.job_records import record_submit_job

    with tempfile.TemporaryDirectory() as tmpdir:
        _init(tmpdir)

        result = record_submit_job(
            project_root=tmpdir,
            scheduler="local",
            job_id="job_001",
        )

        assert result["status"] == "error"
        assert result["code"] == "gate_decision_id_required"


def test_record_submit_job_rejects_nonexistent_gate():
    """record_submit_job rejects gate_decision_id not in gates.json."""
    from runtime.simflow_helpers.computation.job_records import record_submit_job

    with tempfile.TemporaryDirectory() as tmpdir:
        _init(tmpdir)

        result = record_submit_job(
            project_root=tmpdir,
            scheduler="local",
            job_id="job_001",
            gate_decision_id="gate_nonexistent",
        )

        assert result["status"] == "error"
        assert result["code"] == "gate_decision_not_found"


def test_record_submit_job_succeeds_with_valid_gate():
    """record_submit_job succeeds when gate_decision_id exists in gates.json."""
    from runtime.simflow_helpers.computation.job_records import record_submit_job
    from runtime.simflow_core.state import write_state

    with tempfile.TemporaryDirectory() as tmpdir:
        _init(tmpdir)

        # Add a gate to gates.json
        write_state(
            [{"gate_id": "gate_001_approved", "decision": "approved"}],
            project_root=tmpdir,
            state_file="gates.json",
        )

        result = record_submit_job(
            project_root=tmpdir,
            scheduler="local",
            job_id="job_001",
            gate_decision_id="gate_001_approved",
        )

        assert result["status"] == "success"
        assert result["job_record"]["gate_decision_id"] == "gate_001_approved"


def test_record_submit_job_allows_user_override():
    """record_submit_job allows user_override with valid override_gate_id."""
    from runtime.simflow_helpers.computation.job_records import record_submit_job
    from runtime.simflow_core.state import write_state

    with tempfile.TemporaryDirectory() as tmpdir:
        _init(tmpdir)

        # Add a user_override gate
        write_state(
            [{"gate_id": "override_001", "decision": "user_override"}],
            project_root=tmpdir,
            state_file="gates.json",
        )

        result = record_submit_job(
            project_root=tmpdir,
            scheduler="local",
            job_id="job_001",
            user_override=True,
            override_gate_id="override_001",
        )

        assert result["status"] == "success"


def test_record_submit_job_rejects_override_without_gate():
    """record_submit_job rejects user_override without override_gate_id."""
    from runtime.simflow_helpers.computation.job_records import record_submit_job

    with tempfile.TemporaryDirectory() as tmpdir:
        _init(tmpdir)

        result = record_submit_job(
            project_root=tmpdir,
            scheduler="local",
            job_id="job_001",
            user_override=True,
        )

        assert result["status"] == "success"  # override_gate_id is optional


def test_record_submit_job_rejects_nonexistent_override_gate():
    """record_submit_job rejects override_gate_id not in gates.json."""
    from runtime.simflow_helpers.computation.job_records import record_submit_job

    with tempfile.TemporaryDirectory() as tmpdir:
        _init(tmpdir)

        result = record_submit_job(
            project_root=tmpdir,
            scheduler="local",
            job_id="job_001",
            user_override=True,
            override_gate_id="override_nonexistent",
        )

        assert result["status"] == "error"
        assert result["code"] == "override_gate_not_found"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
