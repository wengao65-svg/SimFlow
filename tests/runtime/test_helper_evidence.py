#!/usr/bin/env python3
"""Tests for shared helper-evidence metadata extraction."""

import json
from pathlib import Path

from runtime.simflow_core.helper_evidence import (
    SCHEMA_VERSION,
    VALID_PARSER_STATUSES,
    VALID_STATUSES,
    extract_helper_evidence_metadata,
    helper_evidence_summary,
)


ROOT = Path(__file__).resolve().parents[2]


def test_extract_helper_evidence_metadata_normalizes_common_artifact_fields():
    artifact = {
        "artifact_id": "art_metrics",
        "stage": "analysis_visualization",
        "metadata": {
            "schema_version": "simflow.helper_evidence.v1",
            "helper": "summarize_mlp_metrics",
            "evidence_role": "model_metrics_summary",
            "status": "warning",
            "parser_status": "partial",
            "recipe": "mlp_md",
            "claim_ids": ["claim_metrics"],
            "actual_tool_used": {"software": "nep", "support_level": "helper_supported"},
        },
        "lineage": {
            "software": "nep",
            "parameters": {"recipe": "mlp_md"},
        },
    }

    metadata = extract_helper_evidence_metadata(artifact)
    summary = helper_evidence_summary(artifact)

    assert metadata["schema_version"] == "simflow.helper_evidence.v1"
    assert metadata["helper"] == "summarize_mlp_metrics"
    assert metadata["evidence_role"] == "model_metrics_summary"
    assert metadata["helper_status"] == "warning"
    assert metadata["parser_status"] == "partial"
    assert metadata["tool"] == "nep"
    assert metadata["recipe"] == "mlp_md"
    assert metadata["claim_ids"] == ["claim_metrics"]
    assert summary["actual_tool_used"]["support_level"] == "helper_supported"


def test_helper_evidence_schema_matches_runtime_status_vocabularies():
    schema = json.loads((ROOT / "schemas" / "helper_evidence.schema.json").read_text(encoding="utf-8"))

    assert schema["properties"]["schema_version"]["const"] == SCHEMA_VERSION
    assert set(schema["properties"]["status"]["enum"]) == VALID_STATUSES
    assert set(schema["properties"]["parser_status"]["enum"]) == VALID_PARSER_STATUSES
    for field in [
        "schema_version",
        "helper",
        "capability",
        "status",
        "stage",
        "activity",
        "evidence_role",
        "source_files",
        "actual_tool_used",
        "parser_status",
        "claim_limits",
        "warnings",
        "limitations",
        "parent_artifacts",
    ]:
        assert field in schema["required"]
