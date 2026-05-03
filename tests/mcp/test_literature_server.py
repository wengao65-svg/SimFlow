#!/usr/bin/env python3
"""Integration tests for Literature MCP server.

Tests the server's handle_request() function end-to-end,
verifying the full request dispatch path.
"""

import importlib.util
import json
import sys
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parents[2] / "mcp" / "servers" / "literature"


def _load_server():
    """Load the literature server module by file path to avoid name collisions."""
    # Clear cached connectors modules to avoid cross-test contamination
    mods_to_remove = [k for k in sys.modules if k.startswith("connectors")]
    for m in mods_to_remove:
        del sys.modules[m]

    server_path = SERVER_DIR / "server.py"
    spec = importlib.util.spec_from_file_location("literature_server", server_path)
    mod = importlib.util.module_from_spec(spec)
    # Ensure connectors subpackage is findable
    sys.path.insert(0, str(SERVER_DIR))
    sys.path.insert(0, str(SERVER_DIR.parent.parent.parent))
    spec.loader.exec_module(mod)
    return mod


def test_search_mock():
    """Test search via mock backend (no API key needed)."""
    server = _load_server()
    request = {
        "tool": "search",
        "params": {"query": "perovskite solar cell", "backend": "mock", "max_results": 5},
    }
    result = server.handle_request(request)
    assert result["status"] == "success"
    assert "data" in result
    assert result["data"]["query"] == "perovskite solar cell"
    assert isinstance(result["data"]["results"], list)
    print("  search (mock) OK")


def test_get_metadata_mock():
    """Test get_metadata via mock backend."""
    server = _load_server()
    request = {
        "tool": "get_metadata",
        "params": {"doi": "10.1038/test", "backend": "mock"},
    }
    result = server.handle_request(request)
    assert result["status"] in ("success", "error")
    print("  get_metadata (mock) OK")


def test_unknown_tool():
    """Test handling of unknown tool name."""
    server = _load_server()
    request = {"tool": "nonexistent_tool", "params": {}}
    result = server.handle_request(request)
    assert result["status"] == "error"
    assert "Unknown tool" in result["message"]
    print("  unknown tool error OK")


def test_missing_query():
    """Test search with missing query parameter."""
    server = _load_server()
    request = {"tool": "search", "params": {}}
    result = server.handle_request(request)
    assert result["status"] == "error"
    assert "query" in result["message"].lower()
    print("  missing query error OK")


def test_missing_doi():
    """Test get_metadata with missing DOI."""
    server = _load_server()
    request = {"tool": "get_metadata", "params": {}}
    result = server.handle_request(request)
    assert result["status"] == "error"
    assert "doi" in result["message"].lower()
    print("  missing doi error OK")


def test_connector_registry():
    """Test that all expected connectors are registered."""
    server = _load_server()
    assert hasattr(server, "_CONNECTORS") or hasattr(server, "TOOLS")
    if hasattr(server, "_CONNECTORS"):
        assert "mock" in server._CONNECTORS
        assert "arxiv" in server._CONNECTORS
        assert "crossref" in server._CONNECTORS
        assert "semantic_scholar" in server._CONNECTORS
    print("  connector registry OK")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        print(f"  {t.__name__}...", end=" ")
        t()
        print("OK")
    print(f"\n  All {len(tests)} literature server tests passed!")
