#!/usr/bin/env python3
"""Tests for OpenAlex connector and mock unverified tagging.

Covers P0.3:
- OpenAlex connector returns real data (no key required)
- Mock connector tags results as mock_unverified
- Auto-detection defaults to OpenAlex (not mock) without S2_API_KEY
- S2_API_KEY still takes precedence for Semantic Scholar
- Tool descriptions no longer say "mock/dry-run fallback by default"
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parents[2]  # tests/mcp/ -> simflow/
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runtime"))
sys.path.insert(0, str(ROOT / "mcp" / "servers" / "literature"))


def test_mock_connector_tags_results_as_unverified():
    """MockLiteratureConnector must tag results with status='mock_unverified'."""
    from connectors.mock import MockLiteratureConnector

    connector = MockLiteratureConnector()
    results = connector.search("silicon", max_results=5)

    assert len(results) > 0
    for result in results:
        assert result["status"] == "mock_unverified"
        assert result["usable_as_evidence"] is False
        assert result["source"] == "mock"


def test_mock_connector_get_metadata_tags_as_unverified():
    """MockLiteratureConnector.get_metadata must tag results as mock_unverified."""
    from connectors.mock import MockLiteratureConnector

    connector = MockLiteratureConnector()
    meta = connector.get_metadata("10.1103/PhysRevB.97.165202")

    assert meta is not None
    assert meta["status"] == "mock_unverified"
    assert meta["usable_as_evidence"] is False
    assert meta["source"] == "mock"


def test_openalex_connector_import():
    """OpenAlexConnector can be imported and instantiated."""
    from connectors.openalex import OpenAlexConnector

    connector = OpenAlexConnector()
    assert connector is not None
    assert hasattr(connector, "search")
    assert hasattr(connector, "get_metadata")


def test_openalex_normalize_work():
    """OpenAlexConnector._normalize_work correctly parses a work record."""
    from connectors.openalex import OpenAlexConnector

    work = {
        "id": "https://openalex.org/W123456789",
        "doi": "https://doi.org/10.1000/test.123",
        "title": "Test Paper Title",
        "authorships": [
            {"author": {"display_name": "Alice Smith"}},
            {"author": {"display_name": "Bob Jones"}},
        ],
        "abstract_inverted_index": {
            "We": [0],
            "present": [1],
            "a": [2],
            "test": [3],
        },
        "publication_year": 2024,
        "primary_location": {
            "source": {"display_name": "Test Journal"}
        },
    }

    result = OpenAlexConnector._normalize_work(work)

    assert result is not None
    assert result["doi"] == "10.1000/test.123"
    assert result["title"] == "Test Paper Title"
    assert result["authors"] == ["Alice Smith", "Bob Jones"]
    assert result["abstract"] == "We present a test"
    assert result["year"] == 2024
    assert result["journal"] == "Test Journal"
    assert result["source"] == "OpenAlex"


def test_openalex_normalize_empty_work():
    """OpenAlexConnector._normalize_work handles empty/invalid work."""
    from connectors.openalex import OpenAlexConnector

    assert OpenAlexConnector._normalize_work({}) is None
    assert OpenAlexConnector._normalize_work(None) is None
    assert OpenAlexConnector._normalize_work("not a dict") is None


def test_auto_detection_returns_openalex_without_s2_key():
    """_get_connector('auto') returns OpenAlexConnector without S2_API_KEY."""
    env_backup = os.environ.pop("S2_API_KEY", None)

    try:
        from server import _get_connector
        connector = _get_connector("auto")
        from connectors.openalex import OpenAlexConnector
        assert isinstance(connector, OpenAlexConnector), \
            f"expected OpenAlexConnector, got {type(connector).__name__}"
    finally:
        if env_backup is not None:
            os.environ["S2_API_KEY"] = env_backup


def test_auto_detection_returns_semantic_scholar_with_s2_key():
    """_get_connector('auto') returns SemanticScholar when S2_API_KEY is set."""
    env_backup = os.environ.pop("S2_API_KEY", None)
    os.environ["S2_API_KEY"] = "test_key_12345"

    try:
        from server import _get_connector
        connector = _get_connector("auto")
        from connectors.semantic_scholar import SemanticScholarConnector
        assert isinstance(connector, SemanticScholarConnector), \
            f"expected SemanticScholarConnector, got {type(connector).__name__}"
    finally:
        os.environ.pop("S2_API_KEY", None)
        if env_backup is not None:
            os.environ["S2_API_KEY"] = env_backup


def test_explicit_backend_mock():
    """Explicit backend='mock' returns MockLiteratureConnector."""
    from server import _get_connector
    connector = _get_connector("mock")
    from connectors.mock import MockLiteratureConnector
    assert isinstance(connector, MockLiteratureConnector)


def test_explicit_backend_openalex():
    """Explicit backend='openalex' returns OpenAlexConnector."""
    from server import _get_connector
    connector = _get_connector("openalex")
    from connectors.openalex import OpenAlexConnector
    assert isinstance(connector, OpenAlexConnector)


def test_explicit_backend_arxiv():
    """Explicit backend='arxiv' returns ArxivConnector."""
    from server import _get_connector
    connector = _get_connector("arxiv")
    from connectors.arxiv import ArxivConnector
    assert isinstance(connector, ArxivConnector)


def test_unknown_backend_falls_back_to_mock():
    """Unknown backend string falls back to MockLiteratureConnector."""
    from server import _get_connector
    connector = _get_connector("nonexistent_backend")
    from connectors.mock import MockLiteratureConnector
    assert isinstance(connector, MockLiteratureConnector)


def test_tool_descriptions_do_not_mention_mock_fallback():
    """Tool descriptions must not say 'mock/dry-run fallback by default'."""
    from server import TOOL_DESCRIPTIONS

    for tool_name, desc in TOOL_DESCRIPTIONS.items():
        assert "mock/dry-run fallback by default" not in desc.lower(), \
            f"{tool_name} description still mentions mock fallback"
        assert "mock fallback" not in desc.lower(), \
            f"{tool_name} description still mentions mock fallback"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
