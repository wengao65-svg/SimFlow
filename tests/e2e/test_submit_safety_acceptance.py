#!/usr/bin/env python3
"""Acceptance tests for real-submit safety boundaries."""

import hashlib
import json
from pathlib import Path

from mcp.servers.hpc.connectors.local import LocalConnector
from runtime.simflow_core.gates import record_gate_decision


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _make_script(project_root: Path) -> Path:
    script = project_root / "job.sh"
    script.write_text("#!/bin/bash\necho approved-local-job\n", encoding="utf-8")
    script.chmod(0o755)
    return script


def _write_submit_evidence(project_root: Path, script: Path, *, credential_scan: bool = True) -> dict:
    script_hash = _sha256_file(script)
    input_hash = "input-manifest-sha256"
    artifacts = project_root / ".simflow" / "artifacts"
    _write_json(
        artifacts / "compute" / "dry_run_report.json",
        {
            "status": "pass",
            "script_hash": script_hash,
            "input_artifact_hash": input_hash,
        },
    )
    _write_json(artifacts / "compute" / "input_validation.json", {"missing_required_files": []})
    _write_json(artifacts / "compute" / "resource_estimate.json", {"status": "pass"})
    if credential_scan:
        _write_json(artifacts / "security" / "credential_scan.json", {"findings": []})
    decision = record_gate_decision(
        "hpc_submit",
        "approved",
        {"reason": "acceptance test approval"},
        project_root=str(project_root),
        agent="pytest",
    )
    return {
        "project_root": str(project_root),
        "gate_decision_id": decision["decision_id"],
        "dry_run_evidence": "compute/dry_run_report.json",
        "script_hash": script_hash,
        "input_artifact_hash": input_hash,
    }


def test_local_submit_requires_gate_decision_not_boolean_or_missing_approval(tmp_path):
    connector = LocalConnector()
    script = _make_script(tmp_path)

    missing = connector.submit(str(script))
    assert missing["status"] == "error"
    assert missing["approval_required"] is True
    assert missing["gate"] == "hpc_submit"

    boolean_only = connector.submit(str(script), approved=True)
    assert boolean_only["status"] == "error"
    assert boolean_only["approval_required"] is True
    assert "Boolean approved is not accepted" in boolean_only["message"]


def test_missing_credential_scan_blocks_submit_even_with_approval(tmp_path):
    connector = LocalConnector()
    script = _make_script(tmp_path)
    kwargs = _write_submit_evidence(tmp_path, script, credential_scan=False)

    result = connector.submit(str(script), **kwargs)

    assert result["status"] == "error"
    assert result["code"] == "hpc_submit_gate_blocked"
    assert result["approval_required"] is True
    assert "credentials_clean" in result["gate_result"]["conditions"]["unmet"]


def test_changed_job_script_hash_invalidates_prior_approval(tmp_path):
    connector = LocalConnector()
    script = _make_script(tmp_path)
    kwargs = _write_submit_evidence(tmp_path, script)
    script.write_text("#!/bin/bash\necho changed-after-approval\n", encoding="utf-8")

    result = connector.submit(str(script), **kwargs)

    assert result["status"] == "error"
    assert result["code"] == "script_hash_mismatch"
    assert result["current_script_hash"] != result["approved_script_hash"]


def test_plugin_root_cannot_be_used_as_submit_project_root(tmp_path):
    connector = LocalConnector()
    script = _make_script(tmp_path)
    script_hash = _sha256_file(script)
    plugin_root = Path(__file__).resolve().parents[2]

    result = connector.submit(
        str(script),
        project_root=str(plugin_root),
        gate_decision_id="gate_decision_fake",
        dry_run_evidence="compute/dry_run_report.json",
        script_hash=script_hash,
        input_artifact_hash="input-manifest-sha256",
    )

    assert result["status"] == "error"
    assert result["code"] == "invalid_project_root"
    assert "plugin root" in result["message"]
