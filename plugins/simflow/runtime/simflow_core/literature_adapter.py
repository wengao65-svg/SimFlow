"""Optional literature metadata enrichment adapter."""

from __future__ import annotations

from typing import Any

from runtime.simflow_helpers.literature import get_connector

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

    connector = get_connector(backend)
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
