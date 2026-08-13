"""Optional literature discovery, verification, and corpus helpers."""

from .corpus import ingest_research_sources, inspect_local_pdf, parse_bibtex, records_relevant_to_query
from .evidence import (
    display_evidence_level,
    initial_evidence_state,
    mark_claim_verified,
    mark_full_text_available,
    mark_full_text_inspected,
)
from .fulltext import acquire_full_text, collect_full_text_candidates, download_full_text
from .identity import (
    authors_compatible,
    canonical_paper_id,
    match_records,
    normalize_arxiv_id,
    normalize_doi,
    normalize_title,
)
from .registry import get_connector, get_connectors
from .service import LiteratureService, merge_paper_records
from .metrics import summarize_literature_metrics

__all__ = [
    "LiteratureService",
    "acquire_full_text",
    "authors_compatible",
    "canonical_paper_id",
    "collect_full_text_candidates",
    "display_evidence_level",
    "download_full_text",
    "get_connector",
    "get_connectors",
    "ingest_research_sources",
    "initial_evidence_state",
    "inspect_local_pdf",
    "mark_claim_verified",
    "mark_full_text_available",
    "mark_full_text_inspected",
    "match_records",
    "merge_paper_records",
    "normalize_arxiv_id",
    "normalize_doi",
    "normalize_title",
    "parse_bibtex",
    "records_relevant_to_query",
    "summarize_literature_metrics",
]
