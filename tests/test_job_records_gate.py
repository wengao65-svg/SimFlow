#!/usr/bin/env python3
"""Tests for compact submit records bound to immutable approvals."""

from __future__ import annotations

import pytest

from runtime.simflow_core.gates import record_gate_decision
from runtime.simflow_core.records import list_project_records
from runtime.simflow_helpers.computation.job_records import record_submit_job


RUN_PLAN_HASH = "a" * 64


def _approve(project_root, run_plan_hash: str = RUN_PLAN_HASH):
    return record_gate_decision(
        "hpc_submit",
        "approved",
        {"run_plan_hash": run_plan_hash},
        project_root=str(project_root),
        agent="pytest",
    )


def test_record_submit_job_requires_gate_decision_id(tmp_path):
    result = record_submit_job(
        project_root=str(tmp_path),
        scheduler="local",
        job_id="job_001",
        run_plan_hash=RUN_PLAN_HASH,
    )
    assert result["status"] == "error"
    assert result["code"] == "gate_decision_id_required"


def test_record_submit_job_requires_run_plan_hash(tmp_path):
    decision = _approve(tmp_path)
    result = record_submit_job(
        project_root=str(tmp_path),
        scheduler="local",
        job_id="job_001",
        gate_decision_id=decision["decision_id"],
    )
    assert result["status"] == "error"
    assert result["code"] == "run_plan_hash_required"


def test_record_submit_job_rejects_nonexistent_gate(tmp_path):
    result = record_submit_job(
        project_root=str(tmp_path),
        scheduler="local",
        job_id="job_001",
        run_plan_hash=RUN_PLAN_HASH,
        gate_decision_id="gate_nonexistent",
    )
    assert result["status"] == "error"
    assert result["code"] == "run_plan_not_approved"


def test_record_submit_job_rejects_gate_for_other_plan(tmp_path):
    decision = _approve(tmp_path, "b" * 64)
    result = record_submit_job(
        project_root=str(tmp_path),
        scheduler="local",
        job_id="job_001",
        run_plan_hash=RUN_PLAN_HASH,
        gate_decision_id=decision["decision_id"],
    )
    assert result["status"] == "error"
    assert result["code"] == "run_plan_not_approved"


def test_record_submit_job_appends_one_compact_run(tmp_path):
    decision = _approve(tmp_path)
    result = record_submit_job(
        project_root=str(tmp_path),
        scheduler="local",
        job_id="job_001",
        run_plan_hash=RUN_PLAN_HASH,
        gate_decision_id=decision["decision_id"],
        status="completed",
    )
    assert result["status"] == "success"
    assert result["record"]["details"]["run_plan_hash"] == RUN_PLAN_HASH
    records = list_project_records(str(tmp_path), kind="run")
    assert len(records) == 1
    assert records[0]["details"]["job_id"] == "job_001"


def test_user_override_bypass_is_not_part_of_record_api(tmp_path):
    with pytest.raises(TypeError):
        record_submit_job(
            project_root=str(tmp_path),
            scheduler="local",
            job_id="job_001",
            run_plan_hash=RUN_PLAN_HASH,
            user_override=True,
        )
