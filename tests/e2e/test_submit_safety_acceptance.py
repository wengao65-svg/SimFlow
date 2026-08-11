#!/usr/bin/env python3
"""Acceptance tests for immutable-plan real-submit safety."""

from __future__ import annotations

from pathlib import Path

import pytest

from mcp.servers.hpc.connectors.local import LocalConnector
from mcp.servers.hpc.run_plan import RunPlanError, build_run_plan, prepare_script
from runtime.simflow_core.gates import record_gate_decision


def _create_plan(project_root: Path, *, credential: bool = False) -> tuple[Path, dict]:
    script = project_root / "job.sh"
    input_file = project_root / "input.dat"
    script.write_text("#!/bin/bash\necho approved-local-job\n", encoding="utf-8")
    script.chmod(0o755)
    input_file.write_text("token=secret-value\n" if credential else "input\n", encoding="utf-8")
    connector = LocalConnector()
    plan = build_run_plan(
        str(project_root),
        {
            "script_path": script.name,
            "input_paths": [input_file.name],
            "scheduler": "local",
            "resources": {"nodes": 1, "ntasks": 1},
        },
        script=script,
        script_generated=False,
        validation=connector.dry_run(str(script)),
    )
    return script, plan


def _approve(project_root: Path, run_plan_hash: str, *, include_hash: bool = True) -> dict:
    conditions = {"reason": "acceptance test approval"}
    if include_hash:
        conditions["run_plan_hash"] = run_plan_hash
    return record_gate_decision(
        "hpc_submit",
        "approved",
        conditions,
        project_root=str(project_root),
        agent="pytest",
    )


def test_local_submit_requires_gate_decision_not_boolean_or_missing_approval(tmp_path):
    connector = LocalConnector()
    script, plan = _create_plan(tmp_path)

    missing = connector.submit(str(script), project_root=str(tmp_path), run_plan_hash=plan["run_plan_hash"])
    assert missing["status"] == "error"
    assert missing["approval_required"] is True
    assert missing["gate"] == "hpc_submit"

    boolean_only = connector.submit(
        str(script),
        project_root=str(tmp_path),
        run_plan_hash=plan["run_plan_hash"],
        approved=True,
    )
    assert boolean_only["status"] == "error"
    assert "Boolean approved is not accepted" in boolean_only["message"]


def test_failed_credential_scan_blocks_submit_even_with_approval(tmp_path):
    connector = LocalConnector()
    script, plan = _create_plan(tmp_path, credential=True)
    decision = _approve(tmp_path, plan["run_plan_hash"])

    result = connector.submit(
        str(script),
        project_root=str(tmp_path),
        run_plan_hash=plan["run_plan_hash"],
        gate_decision_id=decision["decision_id"],
    )

    assert plan["credential_scan"]["status"] == "fail"
    assert result["status"] == "error"
    assert result["code"] == "run_plan_stale"


def test_gate_decision_must_bind_run_plan_hash(tmp_path):
    connector = LocalConnector()
    script, plan = _create_plan(tmp_path)
    decision = _approve(tmp_path, plan["run_plan_hash"], include_hash=False)

    result = connector.submit(
        str(script),
        project_root=str(tmp_path),
        run_plan_hash=plan["run_plan_hash"],
        gate_decision_id=decision["decision_id"],
    )

    assert result["status"] == "error"
    assert result["code"] == "run_plan_approval_mismatch"


def test_gate_decision_for_other_plan_cannot_be_reused(tmp_path):
    connector = LocalConnector()
    script, plan = _create_plan(tmp_path)
    decision = _approve(tmp_path, "0" * 64)

    result = connector.submit(
        str(script),
        project_root=str(tmp_path),
        run_plan_hash=plan["run_plan_hash"],
        gate_decision_id=decision["decision_id"],
    )

    assert result["status"] == "error"
    assert result["code"] == "run_plan_approval_mismatch"


def test_changed_input_or_script_invalidates_prior_approval(tmp_path):
    connector = LocalConnector()
    script, plan = _create_plan(tmp_path)
    decision = _approve(tmp_path, plan["run_plan_hash"])
    (tmp_path / "input.dat").write_text("changed\n", encoding="utf-8")

    result = connector.submit(
        str(script),
        project_root=str(tmp_path),
        run_plan_hash=plan["run_plan_hash"],
        gate_decision_id=decision["decision_id"],
    )

    assert result["status"] == "error"
    assert result["code"] == "run_plan_stale"


def test_unchanged_retry_reuses_approval(tmp_path):
    connector = LocalConnector()
    script, plan = _create_plan(tmp_path)
    decision = _approve(tmp_path, plan["run_plan_hash"])
    kwargs = {
        "project_root": str(tmp_path),
        "run_plan_hash": plan["run_plan_hash"],
        "gate_decision_id": decision["decision_id"],
    }

    assert connector.submit(str(script), **kwargs)["status"] == "success"
    assert connector.submit(str(script), **kwargs)["status"] == "success"


def test_plugin_root_cannot_be_used_as_plan_project_root():
    plugin_root = Path(__file__).resolve().parents[2]
    with pytest.raises((RunPlanError, ValueError), match="plugin root"):
        prepare_script(str(plugin_root), {"script_path": "job.sh"})
