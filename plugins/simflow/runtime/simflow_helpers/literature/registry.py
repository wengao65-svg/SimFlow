"""Connector selection for literature helper operations."""

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
def get_connector(backend: str = "auto"):
    """Return one explicit connector; unknown names fail closed."""
    if backend == "auto":
        from .service import LiteratureService

        return LiteratureService(get_connectors("auto"))

    connector_type = _CONNECTORS.get(backend)
    if connector_type is None:
        return None
    try:
        return connector_type()
    except Exception:
        return None


def get_connectors(backend: str = "auto") -> list:
    """Return the ordered provider set for a multi-source operation."""
    if backend != "auto":
        connector = get_connector(backend)
        return [connector] if connector is not None else []

    ordered = [OpenAlexConnector, CrossrefConnector, ArxivConnector]
    if os.environ.get("S2_API_KEY"):
        ordered.insert(0, SemanticScholarConnector)
    else:
        ordered.append(SemanticScholarConnector)

    connectors = []
    for connector_type in ordered:
        try:
            connectors.append(connector_type())
        except Exception:
            continue
    return connectors


__all__ = ["get_connector", "get_connectors"]
