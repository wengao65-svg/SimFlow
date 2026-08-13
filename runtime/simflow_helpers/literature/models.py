"""Canonical data models for literature helper operations."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ProviderResult:
    """One provider operation with an explicit success or degradation state."""

    provider: str
    operation: str
    status: str
    records: list[dict[str, Any]] = field(default_factory=list)
    error: str = ""
    retryable: bool = False
    query_count: int = 1

    def to_dict(self, *, include_records: bool = True) -> dict[str, Any]:
        result = asdict(self)
        result["record_count"] = len(self.records)
        if not include_records:
            result.pop("records", None)
        return result


@dataclass
class SourceObservation:
    """Provider- or corpus-specific observation retained during record merging."""

    source: str
    identifiers: dict[str, str] = field(default_factory=dict)
    title: str = ""
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    venue: str = ""
    abstract: str = ""
    url: str = ""
    citation_count: int | None = None
    open_access_locations: list[dict[str, Any]] = field(default_factory=list)
    rank: int | None = None
    source_pointer: str = ""
    full_text: dict[str, Any] | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    def to_dict(self, *, include_raw: bool = False) -> dict[str, Any]:
        result = asdict(self)
        if not include_raw:
            result.pop("raw", None)
        return result


@dataclass
class PaperRecord:
    """One deduplicated paper with field provenance and evidence boundaries."""

    paper_id: str
    title: str = ""
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    venue: str = ""
    abstract: str = ""
    identifiers: dict[str, str] = field(default_factory=dict)
    urls: list[str] = field(default_factory=list)
    citation_count: int | None = None
    open_access_locations: list[dict[str, Any]] = field(default_factory=list)
    observations: list[SourceObservation] = field(default_factory=list)
    field_sources: dict[str, list[str]] = field(default_factory=dict)
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    discovery: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["observations"] = [item.to_dict() for item in self.observations]
        return result


@dataclass
class CitationEdge:
    """One traceable citation-graph edge discovered by a provider."""

    source_paper_id: str
    target_paper_id: str
    relation: str
    provider: str
    depth: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FullTextCandidate:
    """A legal full-text location or user-provided local file."""

    url: str = ""
    path: str = ""
    source: str = ""
    access_basis: str = ""
    version: str = ""
    license: str = ""
    is_pdf: bool = True
    verified: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


__all__ = [
    "CitationEdge",
    "FullTextCandidate",
    "PaperRecord",
    "ProviderResult",
    "SourceObservation",
]
