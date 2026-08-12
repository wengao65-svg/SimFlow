"""Tests for the optional runtime literature enrichment adapter."""

from runtime.simflow_core.literature import enrich_research_sources, search_literature


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

    assert result["backend"] == "unknown"
    assert result["enabled"] is True
    assert result["attempted"] == 1
    assert result["enriched"] == 0
    assert result["failed"] == 1
    assert result["metadata_by_source"] == {}
    assert result["errors"] == ["Unknown backend: unknown"]


def test_search_literature_rejects_unknown_backend_without_mock_data():
    result = search_literature("silicon", backend="unknown")

    assert result["status"] == "error"
    assert result["papers"] == []
    assert result["errors"][0]["provider"] == "unknown"
    assert "Unknown backend" in result["errors"][0]["error"]
