"""Optional literature enrichment adapter backed by MCP connectors."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any
import sys

ROOT = Path(__file__).resolve().parents[2]
SERVER_DIR = ROOT / "mcp" / "servers" / "literature"

if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_SERVER_SPEC = importlib.util.spec_from_file_location("simflow_literature_server", SERVER_DIR / "server.py")
_SERVER_MODULE = importlib.util.module_from_spec(_SERVER_SPEC)
assert _SERVER_SPEC.loader is not None
_SERVER_SPEC.loader.exec_module(_SERVER_MODULE)
_get_connector = _SERVER_MODULE._get_connector
for _module_name in [name for name in list(sys.modules) if name.startswith("connectors")]:
    del sys.modules[_module_name]



def enrich_research_sources(research_sources: dict | None, backend: str = "auto") -> dict[str, Any]:
    """Optionally enrich DOI sources without making offline workflows depend on MCP availability."""
    if not research_sources:
        return {
            "backend": backend,
            "enabled": False,
            "attempted": 0,
            "enriched": 0,
            "failed": 0,
            "metadata_by_source": {},
            "errors": [],
        }

    doi_items = [item for item in research_sources.get("items", []) if item.get("type") == "doi" and item.get("doi")]
    if not doi_items:
        return {
            "backend": backend,
            "enabled": True,
            "attempted": 0,
            "enriched": 0,
            "failed": 0,
            "metadata_by_source": {},
            "errors": [],
        }

    connector = _get_connector(backend)
    if connector is None:
        return {
            "backend": backend,
            "enabled": True,
            "attempted": len(doi_items),
            "enriched": 0,
            "failed": len(doi_items),
            "metadata_by_source": {},
            "errors": [f"Unknown backend: {backend}"],
        }

    metadata_by_source: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    enriched = 0
    failed = 0
    for item in doi_items:
        doi = str(item.get("doi", "")).strip()
        source_id = item.get("source_id", doi)
        try:
            metadata = connector.get_metadata(doi)
        except Exception as exc:
            metadata = None
            errors.append(f"{doi}: {exc}")
        if metadata:
            metadata_by_source[source_id] = {
                **metadata,
                "source": metadata.get("source") or backend,
            }
            enriched += 1
        else:
            failed += 1
            if doi not in " ".join(errors):
                errors.append(f"{doi}: metadata unavailable")

    return {
        "backend": backend,
        "enabled": True,
        "attempted": len(doi_items),
        "enriched": enriched,
        "failed": failed,
        "metadata_by_source": metadata_by_source,
        "errors": errors,
    }
