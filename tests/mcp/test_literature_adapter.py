#!/usr/bin/env python3
"""Tests for the optional literature enrichment adapter."""

from runtime.lib.literature_adapter import enrich_research_sources



def test_enrich_research_sources_uses_mock_backend_for_doi_items():
    result = enrich_research_sources(
        {
            "items": [
                {"source_id": "src_doi_001", "type": "doi", "doi": "10.1103/PhysRevB.97.165202"},
                {"source_id": "src_note_001", "type": "note", "text": "manual note"},
            ]
        },
        backend="mock",
    )

    assert result["backend"] == "mock"
    assert result["enabled"] is True
    assert result["attempted"] == 1
    assert result["enriched"] == 1
    assert result["failed"] == 0
    assert result["errors"] == []
    assert result["metadata_by_source"]["src_doi_001"]["title"] == "First-principles study of silicon crystal structure"



def test_enrich_research_sources_degrades_for_unknown_backend():
    result = enrich_research_sources(
        {
            "items": [
                {"source_id": "src_doi_001", "type": "doi", "doi": "10.1103/PhysRevB.97.165202"},
            ]
        },
        backend="unknown",
    )

    assert result == {
        "backend": "unknown",
        "enabled": True,
        "attempted": 1,
        "enriched": 0,
        "failed": 1,
        "metadata_by_source": {},
        "errors": ["Unknown backend: unknown"],
    }
