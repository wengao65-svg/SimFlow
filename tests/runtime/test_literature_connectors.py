"""Tests for runtime literature connectors and backend selection."""

import os

from runtime.simflow_helpers.literature.connectors import (
    ArxivConnector,
    CrossrefConnector,
    MockLiteratureConnector,
    OpenAlexConnector,
    SemanticScholarConnector,
)
from runtime.simflow_helpers.literature.registry import get_connector, get_connectors
from runtime.simflow_helpers.literature.service import LiteratureService


def test_mock_connector_tags_results_as_unverified():
    connector = MockLiteratureConnector()
    results = connector.search("silicon", max_results=5)

    assert results
    for result in results:
        assert result["status"] == "mock_unverified"
        assert result["usable_as_evidence"] is False
        assert result["source"] == "mock"


def test_mock_connector_get_metadata_tags_as_unverified():
    meta = MockLiteratureConnector().get_metadata("10.1103/PhysRevB.97.165202")

    assert meta is not None
    assert meta["status"] == "mock_unverified"
    assert meta["usable_as_evidence"] is False
    assert meta["source"] == "mock"


def test_openalex_normalize_work():
    work = {
        "id": "https://openalex.org/W123456789",
        "doi": "https://doi.org/10.1000/test.123",
        "title": "Test Paper Title",
        "authorships": [
            {"author": {"display_name": "Alice Smith"}},
            {"author": {"display_name": "Bob Jones"}},
        ],
        "abstract_inverted_index": {"We": [0], "present": [1], "a": [2], "test": [3]},
        "publication_year": 2024,
        "primary_location": {"source": {"display_name": "Test Journal"}},
    }

    result = OpenAlexConnector._normalize_work(work)

    assert result["doi"] == "10.1000/test.123"
    assert result["title"] == "Test Paper Title"
    assert result["authors"] == ["Alice Smith", "Bob Jones"]
    assert result["abstract"] == "We present a test"
    assert result["year"] == 2024
    assert result["journal"] == "Test Journal"
    assert result["source"] == "OpenAlex"


def test_openalex_normalize_empty_work():
    assert OpenAlexConnector._normalize_work({}) is None
    assert OpenAlexConnector._normalize_work(None) is None
    assert OpenAlexConnector._normalize_work("not a dict") is None


def test_crossref_formats_backward_references_for_snowballing():
    connector = CrossrefConnector()
    result = connector._format_item({
        "DOI": "10.1000/seed",
        "title": ["Seed paper"],
        "reference": [
            {"DOI": "10.1000/cited", "article-title": "Cited paper", "author": "Smith", "year": "2020"},
            {"key": "unusable"},
        ],
    })

    assert result["title"] == "Seed paper"
    assert result["references"] == [{
        "doi": "10.1000/cited",
        "identifiers": {"doi": "10.1000/cited"},
        "title": "Cited paper",
        "authors": ["Smith"],
        "year": "2020",
        "source": "Crossref",
    }]


def test_semantic_scholar_normalizes_doi_urls_and_arxiv_ids():
    assert SemanticScholarConnector._paper_id("https://doi.org/10.1000/EXAMPLE") == "DOI:10.1000/example"
    assert SemanticScholarConnector._paper_id("https://arxiv.org/abs/2301.01234v2") == "ARXIV:2301.01234v2"

    result = SemanticScholarConnector()._format_paper({
        "paperId": "s2-id",
        "externalIds": {
            "DOI": "https://doi.org/10.1000/EXAMPLE",
            "ArXiv": "2301.01234v2",
        },
    })

    assert result["doi"] == "10.1000/example"
    assert result["identifiers"] == {
        "semantic_scholar": "s2-id",
        "doi": "10.1000/example",
        "arxiv": "2301.01234",
    }


def test_arxiv_parser_preserves_legacy_category_identifier():
    result = ArxivConnector()._parse_results(
        """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <id>https://arxiv.org/abs/hep-th/9901001v2</id>
            <title>Legacy identifier paper</title>
            <published>1999-01-01T00:00:00Z</published>
          </entry>
        </feed>
        """
    )[0]

    assert result["arxiv_id"] == "hep-th/9901001"
    assert result["arxiv_version"] == "hep-th/9901001v2"


def test_auto_detection_returns_multi_source_service_without_s2_key(monkeypatch):
    monkeypatch.delenv("S2_API_KEY", raising=False)
    connector = get_connector("auto")

    assert isinstance(connector, LiteratureService)
    assert [item.provider_name for item in connector.connectors] == [
        "openalex",
        "crossref",
        "arxiv",
        "semantic_scholar",
    ]


def test_auto_detection_prioritizes_semantic_scholar_with_s2_key(monkeypatch):
    monkeypatch.setenv("S2_API_KEY", "test_key_12345")
    connector = get_connector("auto")

    assert isinstance(connector, LiteratureService)
    assert connector.connectors[0].provider_name == "semantic_scholar"


def test_explicit_backends_and_unknown_backend_fail_closed():
    assert isinstance(get_connector("mock"), MockLiteratureConnector)
    assert isinstance(get_connector("openalex"), OpenAlexConnector)
    assert isinstance(get_connector("arxiv"), ArxivConnector)
    assert isinstance(get_connector("crossref"), CrossrefConnector)
    assert get_connector("nonexistent_backend") is None
    assert get_connectors("nonexistent_backend") == []
