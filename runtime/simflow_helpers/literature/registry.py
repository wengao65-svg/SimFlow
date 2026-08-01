"""Connector selection for optional literature metadata enrichment."""

from __future__ import annotations

import os

from .connectors import (
    ArxivConnector,
    CrossrefConnector,
    MockLiteratureConnector,
    OpenAlexConnector,
    SemanticScholarConnector,
)


_CONNECTORS = {
    "mock": MockLiteratureConnector,
    "arxiv": ArxivConnector,
    "crossref": CrossrefConnector,
    "semantic_scholar": SemanticScholarConnector,
    "openalex": OpenAlexConnector,
}
_MOCK = MockLiteratureConnector()


def get_connector(backend: str = "auto"):
    """Return a literature connector, using tagged mock data as fallback."""
    if backend == "auto":
        if os.environ.get("S2_API_KEY"):
            try:
                return SemanticScholarConnector()
            except Exception:
                pass
        try:
            return OpenAlexConnector()
        except Exception:
            return _MOCK

    connector_type = _CONNECTORS.get(backend)
    if connector_type is None:
        return _MOCK
    try:
        return connector_type()
    except Exception:
        return _MOCK


__all__ = ["get_connector"]
