"""Optional literature metadata enrichment adapter."""

from __future__ import annotations

from typing import Any

from runtime.simflow_helpers.literature import LiteratureService, get_connector, get_connectors

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


def search_literature(
    query: str,
    *,
    backend: str = "auto",
    max_results: int = 20,
) -> dict[str, Any]:
    """Search one or multiple metadata providers without requiring an MCP server."""
    connectors = get_connectors(backend)
    if not connectors:
        return {
            "schema_version": "simflow.literature_result.v1",
            "operation": "search",
            "status": "error",
            "papers": [],
            "provider_results": [],
            "errors": [{"provider": backend, "error": f"Unknown backend: {backend}", "retryable": False}],
        }
    return LiteratureService(connectors).search_papers(query, max_results=max_results)


def search_literature_with_corpus(
    query: str,
    research_sources: dict | None,
    *,
    project_root: str,
    backend: str = "auto",
    max_results: int = 20,
    extract_pdf_metadata: bool = True,
) -> dict[str, Any]:
    """Search local corpus first, then use providers only for a documented gap."""
    connectors = get_connectors(backend)
    if backend != "auto" and not connectors:
        return {
            "schema_version": "simflow.literature_result.v1",
            "operation": "corpus_first_search",
            "status": "error",
            "papers": [],
            "provider_results": [],
            "errors": [{"provider": backend, "error": f"Unknown backend: {backend}", "retryable": False}],
        }
    return LiteratureService(connectors).search_with_corpus(
        query,
        research_sources,
        project_root=project_root,
        max_results=max_results,
        extract_pdf_metadata=extract_pdf_metadata,
    )


def verify_paper_metadata(
    identifier: str,
    *,
    expected: dict[str, Any] | None = None,
    backend: str = "auto",
) -> dict[str, Any]:
    """Cross-check DOI or provider identity across available metadata sources."""
    connectors = get_connectors(backend)
    if not connectors:
        return {
            "schema_version": "simflow.literature_result.v1",
            "operation": "metadata",
            "status": "error",
            "papers": [],
            "provider_results": [],
            "errors": [{"provider": backend, "error": f"Unknown backend: {backend}", "retryable": False}],
        }
    return LiteratureService(connectors).verify_metadata(identifier, expected=expected)


def snowball_literature(
    seed: dict[str, Any] | str,
    *,
    backend: str = "auto",
    directions: tuple[str, ...] = ("references", "citations"),
    depth: int = 1,
    max_results_per_provider: int = 20,
) -> dict[str, Any]:
    """Expand references/cited-by from a seed using connector graph capabilities."""
    connectors = get_connectors(backend)
    if not connectors:
        return {
            "schema_version": "simflow.literature_result.v1",
            "operation": "snowball",
            "status": "error",
            "papers": [],
            "provider_results": [],
            "errors": [{"provider": backend, "error": f"Unknown backend: {backend}", "retryable": False}],
            "edges": [],
        }
    return LiteratureService(connectors).snowball(
        seed,
        directions=directions,
        depth=depth,
        max_results_per_provider=max_results_per_provider,
    )


__all__ = [
    "enrich_research_sources",
    "search_literature",
    "search_literature_with_corpus",
    "snowball_literature",
    "verify_paper_metadata",
]
