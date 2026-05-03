#!/usr/bin/env python3
"""Tests for mock connectors (literature and structure)."""

import json
import sys
from pathlib import Path

CONNECTORS_DIR = Path(__file__).resolve().parents[2] / "mcp" / "servers"


def _setup_connector(server):
    """Add connector package to sys.path for relative imports."""
    conn_dir = str(CONNECTORS_DIR / server)
    if conn_dir not in sys.path:
        sys.path.insert(0, conn_dir)


def test_literature_mock_search():
    _setup_connector("literature")
    from connectors.mock import MockLiteratureConnector
    connector = MockLiteratureConnector()
    results = connector.search("silicon DFT")
    assert isinstance(results, list)
    assert len(results) > 0
    assert "title" in results[0]


def test_literature_mock_get_metadata():
    _setup_connector("literature")
    from connectors.mock import MockLiteratureConnector
    connector = MockLiteratureConnector()
    results = connector.search("silicon")
    if results:
        paper_id = results[0].get("id") or results[0].get("paper_id", "mock_001")
        details = connector.get_metadata(paper_id)
        assert details is None or isinstance(details, dict)


def test_literature_mock_returns_dict_fields():
    _setup_connector("literature")
    from connectors.mock import MockLiteratureConnector
    connector = MockLiteratureConnector()
    results = connector.search("test")
    for paper in results:
        assert isinstance(paper, dict)
        assert "title" in paper


def test_structure_mock_search():
    # Clear any cached connectors module to avoid conflicts
    mods_to_remove = [k for k in sys.modules if k.startswith("connectors")]
    for m in mods_to_remove:
        del sys.modules[m]

    _setup_connector("structure")
    from connectors.mock import MockStructureConnector
    connector = MockStructureConnector()
    results = connector.search("Si")
    assert isinstance(results, list)
    assert len(results) > 0


def test_structure_mock_fetch():
    mods_to_remove = [k for k in sys.modules if k.startswith("connectors")]
    for m in mods_to_remove:
        del sys.modules[m]

    _setup_connector("structure")
    from connectors.mock import MockStructureConnector
    connector = MockStructureConnector()
    results = connector.search("Si")
    if results:
        struct_id = results[0].get("material_id") or results[0].get("id", "mp-149")
        details = connector.get_structure(struct_id)
        assert details is None or isinstance(details, dict)


def test_structure_mock_returns_dict_fields():
    mods_to_remove = [k for k in sys.modules if k.startswith("connectors")]
    for m in mods_to_remove:
        del sys.modules[m]

    _setup_connector("structure")
    from connectors.mock import MockStructureConnector
    connector = MockStructureConnector()
    results = connector.search("Si")
    for struct in results:
        assert isinstance(struct, dict)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        print(f"  {t.__name__}...", end=" ")
        t()
        print("OK")
    print(f"\n  All {len(tests)} tests passed!")
