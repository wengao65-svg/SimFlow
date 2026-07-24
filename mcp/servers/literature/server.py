"""Literature MCP Server.

Provides literature search and management tools.
Supports multiple backends: OpenAlex (default, no key), arXiv, Crossref,
Semantic Scholar (requires S2_API_KEY).
Falls back to mock connector only when network is unreachable.
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
from connectors.openalex import OpenAlexConnector
from mcp.shared.transport import dispatch_request, run_server


_CONNECTORS = {
    "mock": MockLiteratureConnector,
    "arxiv": ArxivConnector,
    "crossref": CrossrefConnector,
    "semantic_scholar": SemanticScholarConnector,
    "openalex": OpenAlexConnector,
}

_mock = MockLiteratureConnector()


def _get_connector(backend: str = "auto"):
    """Get a connector instance, with auto-detection and fallback.

    Auto-detection order:
    1. S2_API_KEY set -> SemanticScholar (richest metadata)
    2. Default -> OpenAlex (free, no key required, real scholarly data)
    3. If OpenAlex fails to instantiate -> mock (with mock_unverified status)

    The mock connector is NEVER the default for 'auto' — it is only a
    last-resort fallback when network access is unavailable. Mock results
    are tagged with status='mock_unverified' and usable_as_evidence=False.
    """
    if backend == "auto":
        import os
        if os.environ.get("S2_API_KEY"):
            try:
                return SemanticScholarConnector()
            except Exception:
                pass
        # OpenAlex is the default: free, no key required, real scholarly data
        try:
            return OpenAlexConnector()
        except Exception:
            return _mock
    cls = _CONNECTORS.get(backend)
    if cls is None:
        return _mock
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
    "search": "Search literature sources. Defaults to OpenAlex (free, no key). Set S2_API_KEY for Semantic Scholar.",
    "get_metadata": "Fetch literature metadata by DOI via OpenAlex (default) or specified backend.",
}

TOOL_SCHEMAS = {
    "search": {
        "type": "object",
        "required": ["query"],
        "properties": {
            "query": {"type": "string"},
            "max_results": {"type": "integer"},
            "backend": {"type": "string"},
        },
        "additionalProperties": False,
    },
    "get_metadata": {
        "type": "object",
        "required": ["doi"],
        "properties": {
            "doi": {"type": "string"},
            "backend": {"type": "string"},
        },
        "additionalProperties": False,
    },
}


def handle_request(request: dict) -> dict:
    """Dispatch a request to the appropriate tool handler."""
    return dispatch_request(request, TOOLS)


if __name__ == "__main__":
    from mcp.shared.stdio_server import run_mcp_server

    run_mcp_server("literature", TOOLS, TOOL_DESCRIPTIONS, TOOL_SCHEMAS, request_handler=handle_request)
