#!/usr/bin/env python3
"""Tests for the common SimFlow result contract."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


def _result_contract():
    try:
        return importlib.import_module("runtime.simflow_core.result_contract")
    except ModuleNotFoundError as exc:
        pytest.fail(str(exc))


def test_normalize_result_outcome_maps_legacy_statuses_and_honors_explicit_override():
    result_contract = _result_contract()

    assert result_contract.normalize_result_outcome("completed") == "success"
    assert result_contract.normalize_result_outcome("needs_inputs") == "waiting"
    assert result_contract.normalize_result_outcome("waiting_for_outputs") == "waiting"
    assert result_contract.normalize_result_outcome("error") == "error"
    assert result_contract.normalize_result_outcome("skipped_optional_dependency") == "skipped"
    assert result_contract.normalize_result_outcome("failure") in {"blocked", "error"}

    explicit = result_contract.build_simflow_result(
        role="helper",
        activity="summarize",
        legacy_status="completed",
        outcome="warning",
    )

    assert explicit["legacy_status"] == "completed"
    assert explicit["outcome"] == "warning"


def test_attach_simflow_result_preserves_top_level_status_fields():
    result_contract = _result_contract()
    result = {
        "status": "needs_inputs",
        "message": "Missing trajectory file",
        "outputs": ["analysis/report.json"],
    }

    attached = result_contract.attach_simflow_result(
        result,
        role="helper",
        activity="analysis_summary",
        legacy_status=result["status"],
        stage="analysis_visualization",
    )

    assert attached is result
    assert attached["status"] == "needs_inputs"
    assert attached["message"] == "Missing trajectory file"
    assert attached["outputs"] == ["analysis/report.json"]
    assert attached["simflow_result"]["schema_version"] == result_contract.SCHEMA_VERSION
    assert attached["simflow_result"]["legacy_status"] == "needs_inputs"
    assert attached["simflow_result"]["outcome"] == "waiting"


def test_result_contract_schema_matches_runtime_enums():
    result_contract = _result_contract()
    schema = json.loads((ROOT / "schemas" / "result_contract.schema.json").read_text(encoding="utf-8"))

    assert schema["properties"]["schema_version"]["const"] == result_contract.SCHEMA_VERSION
    assert set(schema["properties"]["role"]["enum"]) == set(result_contract.ROLES)
    assert set(schema["properties"]["outcome"]["enum"]) == set(result_contract.OUTCOMES)
    assert set(schema["properties"]["state_effect"]["enum"]) == set(result_contract.STATE_EFFECTS)


def test_extract_helper_evidence_payload_supports_nested_and_top_level_records():
    result_contract = _result_contract()
    payload = {"schema_version": "simflow.helper_evidence.v1", "helper": "parser", "status": "success"}

    assert result_contract.extract_helper_evidence_payload({"helper_evidence": payload}) == payload
    assert result_contract.extract_helper_evidence_payload(payload) == payload
    assert result_contract.extract_helper_evidence_payload({"simflow.helper_evidence.v1": payload}) == payload


def test_attach_simflow_result_maps_checkpoint_failure_to_non_warning_outcome():
    result_contract = _result_contract()
    checkpoint = {"status": "failure"}

    result_contract.attach_simflow_result(
        checkpoint,
        role="state_admin",
        activity="restore_checkpoint",
        legacy_status=checkpoint["status"],
        stage="computation",
        state_effect="checkpoint_admin",
    )

    assert checkpoint["simflow_result"]["legacy_status"] == "failure"
    assert checkpoint["simflow_result"]["outcome"] in {"blocked", "error"}
