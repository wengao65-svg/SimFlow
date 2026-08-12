"""Crossref literature connector."""

import json
import os
import urllib.parse
import urllib.request
from typing import Optional
from urllib.error import HTTPError, URLError

from .base import BaseLiteratureConnector
from ..identity import normalize_doi
from ..cache import TTLCache
from ..models import ProviderResult
from ..retry import RetryableError, retry_with_backoff

CROSSREF_API = "https://api.crossref.org"


class CrossrefConnector(BaseLiteratureConnector):
    """Connector for Crossref DOI metadata."""

    provider_name = "crossref"

    def __init__(self):
        self._cache = TTLCache(max_size=128, ttl_seconds=900)
        self._last_error = None
        self._email = os.environ.get("SIMFLOW_CROSSREF_EMAIL", "")

    def search(self, query: str, max_results: int = 20, **kwargs) -> list:
        """Search Crossref for works."""
        self._set_error(None)
        cache_key = "search:{}:{}".format(query, max_results)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        params = urllib.parse.urlencode({
            "query": query,
            "rows": max_results,
            "select": "DOI,title,author,published-print,published-online,issued,abstract,container-title,type,URL",
        })
        url = "{}/works?{}".format(CROSSREF_API, params)

        success, result = retry_with_backoff(
            lambda: self._fetch_json(url)
        )
        if not success:
            self._set_error(result)
            return []

        results = self._parse_results(result)
        self._cache.set(cache_key, results)
        return results

    def get_metadata(self, doi: str) -> Optional[dict]:
        """Get metadata for a specific DOI."""
        self._set_error(None)
        doi = normalize_doi(doi)
        if not doi:
            return None

        cache_key = "meta:{}".format(doi)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        url = "{}/works/{}".format(CROSSREF_API, urllib.parse.quote(doi, safe=""))

        success, result = retry_with_backoff(
            lambda: self._fetch_json(url)
        )
        if not success:
            self._set_error(result)
            return None

        item = result.get("message", {})
        meta = self._format_item(item) if item else None
        if meta:
            self._cache.set(cache_key, meta)
        return meta

    def references_result(self, identifier: str, max_results: int = 20) -> ProviderResult:
        """Return DOI-bearing backward references from Crossref metadata."""
        metadata = self.metadata_result(identifier)
        if metadata.status != "success":
            return ProviderResult(
                provider=self.provider_name,
                operation="references",
                status=metadata.status,
                error=metadata.error,
                retryable=metadata.retryable,
            )
        references = list(metadata.records[0].get("references") or [])[:max_results]
        return ProviderResult(
            provider=self.provider_name,
            operation="references",
            status="success" if references else "empty",
            records=references,
        )

    @staticmethod
    def _fetch_json(url: str) -> dict:
        """Fetch JSON from URL with structured error handling."""
        try:
            email = os.environ.get("SIMFLOW_CROSSREF_EMAIL", "")
            identity = f"mailto:{email}" if email else "https://github.com/wengao65-svg/SimFlow"
            req = urllib.request.Request(url, headers={
                "User-Agent": f"SimFlow/1.2.0-dev.0 ({identity})"
            })
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as e:
            if e.code == 429:
                raise RetryableError("Crossref rate limited: HTTP {}".format(e.code)) from e
            raise
        except URLError as e:
            raise

    def _parse_results(self, data: dict) -> list:
        """Parse Crossref search results."""
        items = data.get("message", {}).get("items", [])
        return [self._format_item(item) for item in items]

    def _format_item(self, item: dict) -> dict:
        """Format a Crossref item to standard format."""
        title_parts = item.get("title", [])
        title = title_parts[0] if title_parts else ""

        authors = []
        for author in item.get("author", []):
            name = "{} {}".format(author.get("given", ""), author.get("family", "")).strip()
            if name:
                authors.append(name)

        pub_date = item.get("published-print") or item.get("published-online") or item.get("issued") or {}
        date_parts = pub_date.get("date-parts", [[]])
        year = date_parts[0][0] if date_parts and date_parts[0] else None

        doi = normalize_doi(item.get("DOI", ""))
        references = []
        for reference in item.get("reference") or []:
            reference_doi = normalize_doi(reference.get("DOI"))
            reference_title = str(reference.get("article-title") or reference.get("volume-title") or "").strip()
            if not reference_doi and not reference_title:
                continue
            first_author = str(reference.get("author") or "").strip()
            references.append({
                "doi": reference_doi,
                "identifiers": {"doi": reference_doi} if reference_doi else {},
                "title": reference_title,
                "authors": [first_author] if first_author else [],
                "year": reference.get("year"),
                "source": "Crossref",
            })
        return {
            "id": doi,
            "title": title,
            "authors": authors,
            "abstract": item.get("abstract", ""),
            "year": year,
            "journal": item.get("container-title", [""])[0] if item.get("container-title") else "",
            "doi": doi,
            "identifiers": {"doi": doi} if doi else {},
            "type": item.get("type", ""),
            "references": references,
            "source": "Crossref",
            "url": "https://doi.org/{}".format(doi) if doi else "",
        }
