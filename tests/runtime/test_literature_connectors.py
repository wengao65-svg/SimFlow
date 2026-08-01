"""Tests for runtime literature connectors and backend selection."""

import os

from runtime.simflow_helpers.literature.connectors import (
    ArxivConnector,
    MockLiteratureConnector,
    OpenAlexConnector,
    SemanticScholarConnector,
)
from runtime.simflow_helpers.literature.registry import get_connector


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


def test_auto_detection_returns_openalex_without_s2_key(monkeypatch):
    monkeypatch.delenv("S2_API_KEY", raising=False)
    assert isinstance(get_connector("auto"), OpenAlexConnector)


def test_auto_detection_returns_semantic_scholar_with_s2_key(monkeypatch):
    monkeypatch.setenv("S2_API_KEY", "test_key_12345")
    assert isinstance(get_connector("auto"), SemanticScholarConnector)


def test_explicit_backends_and_unknown_fallback():
    assert isinstance(get_connector("mock"), MockLiteratureConnector)
    assert isinstance(get_connector("openalex"), OpenAlexConnector)
    assert isinstance(get_connector("arxiv"), ArxivConnector)
    assert isinstance(get_connector("nonexistent_backend"), MockLiteratureConnector)
