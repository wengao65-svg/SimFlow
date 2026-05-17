"""Literature MCP Server.

Provides literature search and management tools.
Supports multiple backends: arxiv, crossref, semantic_scholar.
Falls back to mock connector when credentials are missing.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runtime"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from connectors.mock import MockLiteratureConnector
from connectors.arxiv import ArxivConnector
from connectors.crossref import CrossrefConnector
from connectors.semantic_scholar import SemanticScholarConnector
from mcp.shared.transport import dispatch_request, run_server


_CONNECTORS = {
    "mock": MockLiteratureConnector,
    "arxiv": ArxivConnector,
    "crossref": CrossrefConnector,
    "semantic_scholar": SemanticScholarConnector,
}

_mock = MockLiteratureConnector()


def _get_connector(backend: str = "auto"):
    """Get a connector instance, with auto-detection and fallback."""
    if backend == "auto":
        import os
        if os.environ.get("S2_API_KEY"):
            return SemanticScholarConnector()
        return _mock
    cls = _CONNECTORS.get(backend)
    if cls is None:
        return None
    try:
        return cls()
    except Exception:
        return _mock


def handle_search(params: dict) -> dict:
    """Search for literature."""
    query = params.get("query", "")
    max_results = params.get("max_results", 20)
    backend = params.get("backend", "auto")
    if not query:
        return {"status": "error", "message": "query is required"}

    connector = _get_connector(backend)
    if connector is None:
        return {"status": "error", "message": "Unknown backend: {}".format(backend)}

    results = connector.search(query, max_results=max_results)
    return {
        "status": "success",
        "data": {"query": query, "results": results, "count": len(results)},
    }


def handle_get_metadata(params: dict) -> dict:
    """Get literature metadata by DOI."""
    doi = params.get("doi", "")
    backend = params.get("backend", "auto")
    if not doi:
        return {"status": "error", "message": "doi is required"}

    connector = _get_connector(backend)
    if connector is None:
        return {"status": "error", "message": "Unknown backend: {}".format(backend)}

    metadata = connector.get_metadata(doi)
    if metadata is None:
        return {"status": "error", "message": "DOI not found: {}".format(doi), "code": "NOT_FOUND"}
    return {"status": "success", "data": metadata}


TOOLS = {
    "search": handle_search,
    "get_metadata": handle_get_metadata,
}

TOOL_DESCRIPTIONS = {
    "search": "Search literature sources with mock/dry-run fallback by default.",
    "get_metadata": "Fetch literature metadata by DOI with safe fallback behavior.",
}


def handle_request(request: dict) -> dict:
    """Dispatch a request to the appropriate tool handler."""
    return dispatch_request(request, TOOLS)


if __name__ == "__main__":
    from mcp.shared.stdio_server import run_mcp_server

    run_mcp_server("literature", TOOLS, TOOL_DESCRIPTIONS)
