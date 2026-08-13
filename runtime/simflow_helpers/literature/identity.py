"""Paper identifier normalization and conservative record matching."""

from __future__ import annotations

import hashlib
import re
import unicodedata
import urllib.parse
from difflib import SequenceMatcher
from typing import Any


DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)
ARXIV_NEW_RE = re.compile(r"^(?P<base>\d{4}\.\d{4,5})(?:v(?P<version>\d+))?$", re.IGNORECASE)
ARXIV_OLD_RE = re.compile(
    r"^(?P<base>[a-z-]+(?:\.[a-z]{2})?/\d{7})(?:v(?P<version>\d+))?$",
    re.IGNORECASE,
)


def normalize_doi(value: Any) -> str:
    """Return a lowercase bare DOI, or an empty string when invalid."""
    raw = urllib.parse.unquote(str(value or "").strip())
    raw = re.sub(r"^doi:\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", raw, flags=re.IGNORECASE)
    raw = raw.strip().rstrip(".,;)")
    raw = raw.replace("\u2010", "-").replace("\u2012", "-").replace("\u2013", "-").replace("\u2014", "-")
    raw = re.sub(r"\s+", "", raw)
    return raw.lower() if DOI_RE.match(raw) else ""


def normalize_arxiv_id(value: Any, *, keep_version: bool = False) -> str:
    """Return a normalized arXiv identifier, optionally retaining its version."""
    raw = urllib.parse.unquote(str(value or "").strip())
    raw = re.sub(r"^arxiv:\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"^https?://arxiv\.org/(?:abs|pdf)/", "", raw, flags=re.IGNORECASE)
    raw = raw.removesuffix(".pdf")
    raw = re.sub(r"^10\.48550/arxiv\.", "", raw, flags=re.IGNORECASE)
    match = ARXIV_NEW_RE.match(raw) or ARXIV_OLD_RE.match(raw)
    if not match:
        return ""
    base = match.group("base").lower()
    version = match.group("version")
    return f"{base}v{version}" if keep_version and version else base


def normalize_title(value: Any) -> str:
    """Normalize a title for comparison without changing the displayed title."""
    text = unicodedata.normalize("NFKD", str(value or "")).casefold()
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = "".join(ch if ch.isalnum() else " " for ch in text)
    return " ".join(text.split())


def normalize_author(value: Any) -> str:
    """Normalize one author name for conservative cross-source comparison."""
    text = normalize_title(value)
    parts = text.split()
    if not parts:
        return ""
    return " ".join(parts[-2:])


def identifiers_from_record(record: dict[str, Any]) -> dict[str, str]:
    """Collect normalized identifiers from a connector or corpus record."""
    identifiers = dict(record.get("identifiers") or {})
    doi = normalize_doi(record.get("doi") or identifiers.get("doi"))
    arxiv = normalize_arxiv_id(
        record.get("arxiv_id") or identifiers.get("arxiv") or identifiers.get("arxiv_id")
    )
    normalized: dict[str, str] = {}
    if doi:
        normalized["doi"] = doi
    if arxiv:
        normalized["arxiv"] = arxiv
    for key in ("openalex", "semantic_scholar", "pmid", "pmcid"):
        value = str(identifiers.get(key) or "").strip()
        if value:
            normalized[key] = value
    source = str(record.get("source") or "").casefold()
    source_id = str(record.get("id") or "").strip()
    if source_id and "semantic scholar" in source:
        normalized.setdefault("semantic_scholar", source_id)
    if source_id and "openalex" in source:
        normalized.setdefault("openalex", source_id.rsplit("/", 1)[-1])
    if source_id and "arxiv" in source:
        normalized.setdefault("arxiv", normalize_arxiv_id(source_id))
    return {key: value for key, value in normalized.items() if value}


def canonical_paper_id(record: dict[str, Any]) -> str:
    """Build a stable helper-local paper identity from strongest available data."""
    identifiers = identifiers_from_record(record)
    if identifiers.get("doi"):
        return f"doi:{identifiers['doi']}"
    if identifiers.get("arxiv"):
        return f"arxiv:{identifiers['arxiv']}"
    for key in ("openalex", "semantic_scholar", "pmid", "pmcid"):
        if identifiers.get(key):
            return f"{key}:{identifiers[key]}"
    title = normalize_title(record.get("title"))
    first_author = normalize_author((record.get("authors") or [""])[0])
    year = str(record.get("year") or "")
    digest = hashlib.sha256(f"{title}|{first_author}|{year}".encode("utf-8")).hexdigest()[:16]
    return f"title:{digest}"


def match_records(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    """Compare two records and return a conservative merge decision."""
    left_ids = identifiers_from_record(left)
    right_ids = identifiers_from_record(right)
    for key in ("doi", "arxiv"):
        if left_ids.get(key) and right_ids.get(key) and left_ids[key] != right_ids[key]:
            return {"match": False, "confidence": 0.0, "reason": f"conflicting_{key}"}
    for key in ("doi", "arxiv", "openalex", "semantic_scholar", "pmid", "pmcid"):
        if left_ids.get(key) and left_ids.get(key) == right_ids.get(key):
            return {"match": True, "confidence": 1.0, "reason": f"exact_{key}"}

    left_title = normalize_title(left.get("title"))
    right_title = normalize_title(right.get("title"))
    if not left_title or not right_title:
        return {"match": False, "confidence": 0.0, "reason": "insufficient_identity"}

    title_score = SequenceMatcher(None, left_title, right_title).ratio()
    left_year = _year(left.get("year"))
    right_year = _year(right.get("year"))
    year_compatible = left_year is None or right_year is None or abs(left_year - right_year) <= 1
    left_author = normalize_author((left.get("authors") or [""])[0])
    right_author = normalize_author((right.get("authors") or [""])[0])
    author_compatible = _authors_compatible(left_author, right_author)

    if title_score >= 0.96 and author_compatible and year_compatible:
        return {
            "match": False,
            "confidence": title_score,
            "reason": "title_author_year_candidate",
            "possible_duplicate": True,
        }
    return {
        "match": False,
        "confidence": title_score,
        "reason": "title_only_candidate" if title_score >= 0.90 else "different",
        "possible_duplicate": title_score >= 0.90,
    }


def _year(value: Any) -> int | None:
    try:
        return int(str(value)[:4])
    except (TypeError, ValueError):
        return None


def _authors_compatible(left: str, right: str) -> bool:
    left_parts = left.split()
    right_parts = right.split()
    if not left_parts or not right_parts or left_parts[-1] != right_parts[-1]:
        return False
    if len(left_parts) == 1 or len(right_parts) == 1:
        return True
    return left_parts[0][0] == right_parts[0][0]


def authors_compatible(left: Any, right: Any) -> bool:
    """Return whether two displayed author names can refer to the same person."""
    return _authors_compatible(normalize_author(left), normalize_author(right))


__all__ = [
    "canonical_paper_id",
    "authors_compatible",
    "identifiers_from_record",
    "match_records",
    "normalize_arxiv_id",
    "normalize_author",
    "normalize_doi",
    "normalize_title",
]
