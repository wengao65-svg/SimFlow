#!/usr/bin/env python3
"""Tests for shared helper-evidence metadata extraction."""

from runtime.simflow_core.helper_evidence import (
    extract_helper_evidence_metadata,
    helper_evidence_summary,
)


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
            "actual_tool_used": {"software": "nep", "support_level": "tracked_only"},
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
    assert summary["actual_tool_used"]["support_level"] == "tracked_only"
